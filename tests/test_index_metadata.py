import sqlite3
from contextlib import closing
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.api_client import ApiClient
from app.indexer.database import initialize
from app.indexer.embeddings import get_config
from app.indexer.index import index_project
from app.indexer.metadata import read_metadata
from app.indexer.search import search
from app.indexer.store import save_chunk
from app.service import AgentService


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("EMBEDDING_MODEL", "model-a")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://embeddings:11434")
    project = tmp_path / "project"
    project.mkdir()
    (project / "one.py").write_text("alpha beta")
    embedder = Mock(side_effect=lambda chunks, **kwargs: [[1.0, 0.0] for _ in chunks])
    monkeypatch.setattr("app.indexer.index.embed_batch", embedder)
    return project, project / ".owa" / "index.db", embedder


def snapshot(path):
    with closing(sqlite3.connect(path)) as db:
        return read_metadata(db), db.execute(
            "SELECT path, chunk_index, content, embedding, file_hash FROM documents ORDER BY path, chunk_index"
        ).fetchall()


def test_records_provenance_and_skips_unchanged_files(workspace):
    project, path, embedder = workspace
    index_project(project, path)
    metadata, rows = snapshot(path)
    assert metadata["model"] == "model-a"
    assert metadata["dimensions"] == 2
    assert metadata["format_version"] == 1
    assert len(metadata["endpoint_hash"]) == 64
    assert rows[0][2] == "alpha beta"
    index_project(project, path)
    assert embedder.call_count == 1
    assert snapshot(path) == (metadata, rows)


def test_incremental_update_does_not_reinitialize_fts(workspace, monkeypatch):
    project, path, _ = workspace
    index_project(project, path)
    initialize_spy = Mock(side_effect=AssertionError("must reuse existing schema and FTS"))
    monkeypatch.setattr("app.indexer.index.initialize", initialize_spy)
    (project / "one.py").write_text("updated content")
    index_project(project, path)
    assert snapshot(path)[1][0][2] == "updated content"
    initialize_spy.assert_not_called()


@pytest.mark.parametrize("remove", ["delete", "ignore"])
def test_removed_files_delete_existing_documents_and_fts(workspace, remove):
    project, path, _ = workspace
    index_project(project, path)
    if remove == "delete":
        (project / "one.py").unlink()
    else:
        (project / ".owaignore").write_text("one.py\n")
    index_project(project, path)
    assert snapshot(path)[1] == []
    with closing(sqlite3.connect(path)) as db:
        assert db.execute(
            "SELECT count(*) FROM documents_fts WHERE documents_fts MATCH 'alpha'"
        ).fetchone()[0] == 0


@pytest.mark.parametrize("setting, value", [
    ("EMBEDDING_MODEL", "model-b"),
    ("EMBEDDING_BASE_URL", "http://another-host:11434"),
])
def test_identity_change_reembeds_unchanged_files(workspace, monkeypatch, setting, value):
    project, path, embedder = workspace
    index_project(project, path)
    before, _ = snapshot(path)
    monkeypatch.setenv(setting, value)
    index_project(project, path)
    after, _ = snapshot(path)
    assert embedder.call_count == 2
    assert before != after


def test_failed_model_rebuild_preserves_previous_database(workspace, monkeypatch):
    project, path, embedder = workspace
    index_project(project, path)
    previous = path.read_bytes()
    monkeypatch.setenv("EMBEDDING_MODEL", "model-b")
    embedder.side_effect = RuntimeError("embedding unavailable")
    with pytest.raises(RuntimeError, match="previous index unchanged"):
        index_project(project, path)
    assert path.read_bytes() == previous
    assert not list(path.parent.glob(".index-*"))


def test_partial_worker_failure_does_not_publish_other_changes(workspace):
    project, path, embedder = workspace
    index_project(project, path)
    previous = path.read_bytes()
    (project / "one.py").write_text("updated")
    (project / "two.py").write_text("failure")

    def embeddings(chunks, **kwargs):
        if chunks == ["failure"]:
            raise RuntimeError("unavailable")
        return [[1.0, 0.0] for _ in chunks]

    embedder.side_effect = embeddings
    with pytest.raises(RuntimeError):
        index_project(project, path)
    assert path.read_bytes() == previous


@pytest.mark.parametrize("vectors", [[], [[1.0], [1.0]], [[]], [[True, 0]],
                                     [[float("nan"), 0]], [[float("inf"), 0]]])
def test_invalid_batch_never_publishes_new_index(workspace, vectors):
    project, path, embedder = workspace
    embedder.side_effect = None
    embedder.return_value = vectors
    with pytest.raises(RuntimeError):
        index_project(project, path)
    assert not path.exists()


def test_dimension_change_requires_force_and_keeps_old_index(workspace):
    project, path, embedder = workspace
    index_project(project, path)
    before = path.read_bytes()
    (project / "one.py").write_text("updated")
    embedder.side_effect = lambda chunks, **kwargs: [[1.0, 0.0, 0.0] for _ in chunks]
    with pytest.raises(RuntimeError):
        index_project(project, path)
    assert path.read_bytes() == before
    index_project(project, path, force=True)
    assert snapshot(path)[0]["dimensions"] == 3


def test_legacy_index_is_rebuilt_without_claiming_old_vector_identity(workspace):
    project, path, embedder = workspace
    initialize(path)
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE index_metadata")
        save_chunk(db, "one.py", 0, "old content", [0.0, 1.0], "old-hash")
    index_project(project, path)
    metadata, rows = snapshot(path)
    assert metadata["model"] == "model-a"
    assert rows[0][2] == "alpha beta"
    embedder.assert_called_once()


def test_shorter_empty_and_deleted_files_remove_stale_chunks_and_fts(workspace, monkeypatch):
    project, path, _ = workspace
    monkeypatch.setattr("app.indexer.index.chunk_text", lambda text: text.splitlines())
    (project / "one.py").write_text("alpha\nobsolete")
    index_project(project, path)
    assert len(snapshot(path)[1]) == 2
    (project / "one.py").write_text("alpha")
    index_project(project, path)
    assert len(snapshot(path)[1]) == 1
    with closing(sqlite3.connect(path)) as db:
        assert db.execute("SELECT count(*) FROM documents_fts WHERE documents_fts MATCH 'obsolete'").fetchone()[0] == 0
    (project / "one.py").write_text("")
    index_project(project, path)
    assert snapshot(path)[1] == []
    (project / "one.py").unlink()
    index_project(project, path)
    assert snapshot(path)[1] == []


def test_configuration_is_frozen_across_workers_and_credentials_are_not_stored(workspace, monkeypatch):
    project, path, embedder = workspace
    monkeypatch.setenv("EMBEDDING_BASE_URL", "http://user:secret@embeddings:11434")
    config = get_config()
    (project / "two.py").write_text("second")

    def embeddings(chunks, **kwargs):
        assert kwargs["config"] == config
        monkeypatch.setenv("EMBEDDING_MODEL", "changed-mid-run")
        return [[1.0, 0.0] for _ in chunks]

    embedder.side_effect = embeddings
    index_project(project, path)
    assert snapshot(path)[0]["model"] == "model-a"
    assert b"secret" not in path.read_bytes()


@pytest.mark.parametrize("legacy", [False, True])
def test_incompatible_index_uses_lexical_search_without_embedding(workspace, monkeypatch, legacy):
    project, path, _ = workspace
    index_project(project, path)
    if legacy:
        with sqlite3.connect(path) as db:
            db.execute("DROP TABLE index_metadata")
    else:
        monkeypatch.setenv("EMBEDDING_MODEL", "model-b")
    embedder = Mock(side_effect=AssertionError("must not embed"))
    monkeypatch.setattr("app.indexer.search.embed", embedder)
    before = path.read_bytes()
    results = search(path, "alpha")
    assert results[0]["path"] == "one.py"
    assert results[0]["semantic_score"] == 0
    assert results[0]["lexical_score"] > 0
    assert path.read_bytes() == before
    embedder.assert_not_called()


def test_query_dimension_mismatch_and_corrupt_vectors_fall_back(workspace, monkeypatch):
    project, path, _ = workspace
    index_project(project, path)
    monkeypatch.setattr("app.indexer.search.embed", lambda *args, **kwargs: [1.0])
    assert search(path, "alpha")[0]["semantic_score"] == 0
    monkeypatch.setattr("app.indexer.search.embed", lambda *args, **kwargs: [1.0, 0.0])
    with sqlite3.connect(path) as db:
        db.execute("UPDATE documents SET embedding = 'broken JSON'")
    assert search(path, "alpha")[0]["semantic_score"] == 0


def test_compatible_search_uses_semantic_scores(workspace, monkeypatch):
    project, path, _ = workspace
    index_project(project, path)
    embedder = Mock(return_value=[1.0, 0.0])
    monkeypatch.setattr("app.indexer.search.embed", embedder)
    assert search(path, "alpha")[0]["semantic_score"] == 1
    embedder.assert_called_once_with("alpha", config=get_config())


def test_status_and_api_force_rebuild(workspace, monkeypatch):
    project, path, _ = workspace
    index_project(project, path)
    service = AgentService(project, agent=object())
    assert service.status()["embedding"]["compatible"]
    monkeypatch.setenv("EMBEDDING_MODEL", "model-b")
    assert not service.status()["embedding"]["compatible"]
    with TestClient(create_app(service, api_key="secret")) as client:
        result = client.get("/status", headers={"X-API-Key": "secret"}).json()
        assert result["embedding"]["reason"] == "embedding model has changed"
        assert client.post("/index?force=true").status_code == 401
        result = client.post("/index?force=true", headers={"X-API-Key": "secret"})
        assert result.status_code == 200
    assert snapshot(path)[0]["model"] == "model-b"


def test_api_client_forwards_force_flag():
    session = Mock()
    client = ApiClient("http://server", session=session)
    client.index(force=True)
    assert session.post.call_args.args[0] == "http://server/index?force=true"
