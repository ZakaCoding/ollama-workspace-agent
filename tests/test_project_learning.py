import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.agent.context import ContextBuilder
from app.agent.core import Agent, task_requires_code_search, task_is_read_only
from app.agent.project import build_project_context
from app.indexer.index import iter_project_files
from app.indexer.search import search


@pytest.mark.parametrize("task", [
    "learn this project", "please understand this codebase", "read all md and learn",
    "Give me an overview of this repository", "Read all markdown files",
])
def test_learning_requests_use_read_only_grounding(task):
    assert task_is_read_only(task)
    assert task_requires_code_search(task)


def test_learning_and_explicit_edit_still_routes_to_tools():
    task = "Learn this project and fix calculator.py"
    assert not task_is_read_only(task)
    assert not task_requires_code_search(task)


def test_legacy_index_without_fts_is_searchable_without_modification(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE documents (id INTEGER PRIMARY KEY, path TEXT, chunk_index INTEGER, content TEXT, embedding BLOB)")
        db.execute("INSERT INTO documents VALUES (1, 'calculator.py', 0, 'def add(a, b): return a + b', '[1,0]')")
    original = path.read_bytes()
    monkeypatch.setattr("app.indexer.search.embed", lambda *args, **kwargs: pytest.fail("legacy vectors have unknown identity"))
    result = search(path, "add")
    assert result[0]["path"] == "calculator.py"
    assert result[0]["lexical_score"] > 0
    assert path.read_bytes() == original
    assert ContextBuilder().build(search(path, "add function"))


def test_project_overview_reads_current_docs_without_index_or_embeddings(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text("A calculator project. Run python -m unittest.")
    (tmp_path / "main.py").write_text("from calculator import add")
    monkeypatch.setattr("app.agent.core.WORKSPACE", tmp_path)
    monkeypatch.setattr("app.agent.core.search", lambda *args, **kwargs: pytest.fail("overview does not need an index"))
    agent = Agent()
    context = agent._build_search_context("learn this project")
    assert "A calculator project" in context
    assert "[README.md#chunk=0]" in context
    assert "README.md#chunk=0" in agent._allowed_citations
    assert "bounded overview" in context
    assert not (tmp_path / ".owa" / "index.db").exists()


@pytest.mark.parametrize("tokens", [2048, 8192])
def test_overview_honors_context_budget_and_limits_selected_files(tmp_path, tokens):
    for number in range(30):
        (tmp_path / f"file{number}.md").write_text("document content\n" * 1000)
    builder = ContextBuilder(model_context_tokens=tokens)
    context, citations = build_project_context(tmp_path, builder)
    assert len(context) <= builder.max_chars
    assert 0 < len(citations) <= 6
    assert "excerpt truncated" in context


def test_discovery_skips_environments_ignored_directories_and_symlinks(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "README.md").write_text("project")
    for name in (".venv312", "node_modules", ".owa", ".codex", "ignored", "custom_env"):
        directory = workspace / name
        directory.mkdir()
        (directory / "secret.md").write_text("not project evidence")
    (workspace / "custom_env" / "pyvenv.cfg").write_text("home = python")
    (workspace / ".owaignore").write_text("ignored\n")
    outside = tmp_path / "outside.md"
    outside.write_text("outside workspace")
    (workspace / "linked.md").symlink_to(outside)
    (workspace / "linked_dir").symlink_to(tmp_path, target_is_directory=True)
    assert [p.name for p in iter_project_files(workspace)] == ["README.md"]
    context, _ = build_project_context(workspace, ContextBuilder())
    assert "not project evidence" not in context
    assert "outside workspace" not in context


def test_ignore_matching_does_not_use_workspace_parent_names(tmp_path):
    workspace = tmp_path / "build" / "project"
    workspace.mkdir(parents=True)
    (workspace / "README.md").write_text("source")
    assert [p.name for p in iter_project_files(workspace)] == ["README.md"]


def test_overview_bounds_long_paths_and_accepts_relative_workspace(tmp_path, monkeypatch):
    directory = tmp_path
    for _ in range(5):
        directory = directory / ("nested" * 30)
        directory.mkdir()
    (directory / "README.md").write_text("project documentation " * 500)
    monkeypatch.chdir(tmp_path)
    builder = ContextBuilder(model_context_tokens=2048)
    context, citations = build_project_context(Path("."), builder)
    assert len(context) <= builder.max_chars
    assert not citations  # Citation headers alone exceed the available budget.
