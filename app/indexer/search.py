import json
import math
import re
import sqlite3
from pathlib import Path
from contextlib import closing

import httpx
from rich.console import Console

from app.indexer.embeddings import embed, get_config
from app.indexer.metadata import compatibility_reason, read_metadata, vector_dimensions
from app.indexer.reranker import rerank

console = Console(stderr=True)


def cosine_similarity(
    a: list[float],
    b: list[float],
) -> float:

    if len(a) != len(b):
        raise ValueError("Vectors must have the same dimensions")

    dot = sum(x * y for x, y in zip(a, b))

    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def keyword_similarity(query: str, content: str) -> float:

    query_terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
    content_terms = set(re.findall(r"[a-z0-9_]+", content.lower()))

    if not query_terms:
        return 0.0

    return len(query_terms & content_terms) / len(query_terms)


def _fts_query(query: str) -> str:
    terms = re.findall(r"[a-z0-9_]+", query.lower())
    return " OR ".join(f'"{term}"' for term in terms)


def _fts_scores(db: sqlite3.Connection, query: str) -> dict[int, float]:
    match_query = _fts_query(query)
    if not match_query:
        return {}

    rows = db.execute(
        """
        SELECT rowid, bm25(documents_fts)
        FROM documents_fts
        WHERE documents_fts MATCH ?
        ORDER BY bm25(documents_fts)
        """,
        (match_query,),
    ).fetchall()
    if not rows:
        return {}

    best = min(row[1] for row in rows)
    worst = max(row[1] for row in rows)
    spread = worst - best
    return {
        rowid: 1.0 if spread == 0 else (worst - rank) / spread
        for rowid, rank in rows
    }


def search(
    db_path: str | Path,
    query: str,
    limit: int = 5,
) -> list[dict]:

    config = get_config()
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("BEGIN")
        metadata = read_metadata(db)
        rows = db.execute(
        """
        SELECT
            id,
            path,
            chunk_index,
            content,
            embedding
        FROM documents
        """
        ).fetchall()
        fts_scores = _fts_scores(db, query)

    if not rows:
        return []
    reason = compatibility_reason(metadata, config)
    query_vector = None
    if reason is None:
        try:
            candidate = embed(query, config=config)
            if vector_dimensions(candidate) == metadata["dimensions"]:
                query_vector = candidate
            else:
                reason = "query embedding dimensions do not match the index"
        except (httpx.HTTPError, RuntimeError, ValueError):
            reason = "query embedding is unavailable or invalid"
    if reason:
        console.print(f"[yellow]Using lexical search: {reason}. Run /index --force to rebuild.[/yellow]")

    results = []

    for (
        document_id,
        path,
        chunk_index,
        content,
        embedding_json,
    ) in rows:

        keyword_score = keyword_similarity(query, content)
        semantic_score = 0.0
        if query_vector is not None:
            try:
                vector = json.loads(embedding_json)
                if vector_dimensions(vector) != metadata["dimensions"]:
                    raise ValueError("Stored vector dimensions do not match metadata")
                semantic_score = cosine_similarity(query_vector, vector)
            except (TypeError, ValueError):
                console.print("[yellow]Invalid stored vector; using lexical score. Run /index --force.[/yellow]")
        lexical_score = fts_scores.get(document_id, keyword_score)
        score = (
            0.55 * semantic_score
            + 0.30 * lexical_score
            + 0.15 * keyword_score
        )

        results.append(
            {
                "id": document_id,
                "path": path,
                "chunk_index": chunk_index,
                "content": content,
                "score": score,
                "semantic_score": semantic_score,
                "lexical_score": lexical_score,
                "keyword_score": keyword_score,
            }
        )

    return rerank(query, results, limit)
