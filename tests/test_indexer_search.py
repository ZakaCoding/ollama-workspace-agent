import sqlite3

import pytest

from app.agent.context import ContextBuilder
from app.indexer.relevance import exact_signals
from app.indexer.search import keyword_similarity

from app.indexer.database import initialize
from app.indexer.search import search
from app.indexer.store import save_chunk
from app.indexer.reranker import rerank
from app.indexer.embeddings import get_config
from app.indexer.metadata import write_metadata


def test_search_combines_embedding_and_exact_term_relevance(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    initialize(db_path)

    with sqlite3.connect(db_path) as db:
        write_metadata(db, get_config(), 2)
        save_chunk(db, "app/router.py", 0, "def route_request(): pass", [1.0, 0.0])
        save_chunk(db, "app/other.py", 0, "def handle_request(): pass", [0.99, 0.01])

    monkeypatch.setattr(
        "app.indexer.search.embed",
        lambda _query, **kwargs: [0.99, 0.01],
    )

    results = search(db_path, "route_request", limit=2)

    assert results[0]["path"] == "app/router.py"
    assert results[0]["semantic_score"] > 0
    assert results[0]["lexical_score"] > results[1]["lexical_score"]


def test_database_fts_index_tracks_updates_and_deletes(tmp_path):
    db_path = tmp_path / "index.db"
    initialize(db_path)

    with sqlite3.connect(db_path) as db:
        save_chunk(db, "app/example.py", 0, "old_symbol", [1.0])
        assert db.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'old_symbol'"
        ).fetchone()[0] == 1

        save_chunk(db, "app/example.py", 0, "new_symbol", [1.0])
        db.execute("DELETE FROM documents WHERE path = ?", ("app/example.py",))
        assert db.execute(
            "SELECT COUNT(*) FROM documents_fts WHERE documents_fts MATCH 'new_symbol'"
        ).fetchone()[0] == 0


def test_local_reranker_prefers_exact_phrase_over_semantic_score():
    results = rerank(
        "route_request",
        [
            {"path": "app/other.py", "content": "route handling", "score": 0.95},
            {"path": "app/router.py", "content": "def route_request(): pass", "score": 0.80},
        ],
        limit=2,
    )

    assert results[0]["path"] == "app/router.py"


@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize(
    "query,target_path,target_content,other_path,other_content",
    [
        ("Where is app/router.py?", "app/router.py", "dispatch incoming calls",
         "app/other.py", "app py router utilities"),
        ('Find "connection refused" in the error handling', "app/errors.py",
         "raise Error('connection   refused')", "app/network.py",
         "connection error handling refused in the connection"),
        ("Where is routeRequest implemented?", "app/router.js",
         "function routeRequest() {}", "app/other.js", "function routeRequestExtra() {}"),
        ("Where is route_request implemented?", "app/router.py",
         "def route_request(): pass", "app/other.py", "def route_request_extra(): pass"),
    ],
)
def test_targeted_retrieval_with_and_without_fts(
    tmp_path, monkeypatch, legacy, query, target_path, target_content, other_path, other_content,
):
    db_path = tmp_path / "index.db"
    initialize(db_path)
    with sqlite3.connect(db_path) as db:
        if not legacy:
            write_metadata(db, get_config(), 2)
        save_chunk(db, other_path, 0, other_content, [1.0, 0.0])
        save_chunk(db, target_path, 4, target_content, [0.8, 0.6])
        if legacy:
            db.execute("DROP TABLE documents_fts")
    monkeypatch.setattr("app.indexer.search.embed", lambda *args, **kwargs: [1.0, 0.0])
    results = search(db_path, query, limit=2)
    assert results[0]["path"] == target_path
    assert target_path in ContextBuilder().build(results[:1])


@pytest.mark.parametrize("query", ["route request", "route_request", "routeRequest"])
def test_identifier_parts_are_searchable(query):
    assert keyword_similarity(query, "routeRequest route_request") == 1.0


@pytest.mark.parametrize("query,path", [
    ("app/router.py", "tests/router.py"),
    ("router.py", "app/not_router.py"),
    ("app/router.py", "app/other.py"),
])
def test_path_signal_requires_complete_reference(query, path):
    assert exact_signals(query, path, "")["path_score"] == 0


def test_exact_phrases_use_word_boundaries():
    assert exact_signals('find "connect"', "a.py", "disconnected")["phrase_score"] == 0


@pytest.mark.parametrize("query,limit", [("", 5), ("???", 5), ("route", 0), ("route", -1)])
def test_empty_search_does_not_open_database(tmp_path, query, limit):
    assert search(tmp_path / "missing.db", query, limit) == []
