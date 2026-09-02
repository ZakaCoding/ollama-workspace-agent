import sqlite3

from app.indexer.database import initialize
from app.indexer.search import search
from app.indexer.store import save_chunk


def test_search_combines_embedding_and_exact_term_relevance(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    initialize(db_path)

    with sqlite3.connect(db_path) as db:
        save_chunk(db, "app/router.py", 0, "def route_request(): pass", [1.0, 0.0])
        save_chunk(db, "app/other.py", 0, "def handle_request(): pass", [0.99, 0.01])

    monkeypatch.setattr(
        "app.indexer.search.embed",
        lambda _query: [0.99, 0.01],
    )

    results = search(db_path, "route_request", limit=2)

    assert results[0]["path"] == "app/router.py"
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