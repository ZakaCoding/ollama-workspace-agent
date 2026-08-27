import json
import math
import re
import sqlite3
from pathlib import Path

import httpx

from app.indexer.embeddings import embed


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


def search(
    db_path: str | Path,
    query: str,
    limit: int = 5,
) -> list[dict]:

    try:
        query_vector = embed(query)
    except httpx.HTTPError:
        query_vector = None

    db = sqlite3.connect(db_path)

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

    db.close()

    results = []

    for (
        document_id,
        path,
        chunk_index,
        content,
        embedding_json,
    ) in rows:

        vector = json.loads(embedding_json)

        if query_vector is None:
            score = keyword_similarity(query, content)
        else:
            score = cosine_similarity(
                query_vector,
                vector,
            )

        results.append(
            {
                "id": document_id,
                "path": path,
                "chunk_index": chunk_index,
                "content": content,
                "score": score,
            }
        )

    results.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return results[:limit]
