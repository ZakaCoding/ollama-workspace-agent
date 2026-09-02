"""
OwA Evaluation Suite — Priority 7 from PLAN.md.

Fixed questions with expected files/tools/citations.
Measures: correct file, correct tool, citation present, hallucination count.
All tests run without a live LLM or index (pure routing/logic layer).
"""
import sqlite3

import pytest

from app.agent.context import ContextBuilder
from app.agent.core import (
    _tools_for_task,
    task_is_changelog_request,
    task_is_commit_message_request,
    task_is_read_only,
    task_is_resume_request,
    task_requires_code_search,
    task_requires_git_tools,
)
from app.agent.verifier import (
    detect_fake_narration,
    validate_mentioned_paths,
    verify_evidence_citations,
)
from app.indexer.database import initialize
from app.indexer.reranker import rerank
from app.indexer.search import search
from app.indexer.store import save_chunk


# ---------------------------------------------------------------------------
# Routing correctness (25 fixed questions)
# ---------------------------------------------------------------------------

SEARCH_QUESTIONS = [
    "Where is hybrid search implemented?",
    "Which files contain FTS5 logic?",
    "Where is the Ollama client configured?",
    "What tools does OwA provide?",
    "How does the agent execute commands?",
    "Where is authentication handled?",
    "Where is the database connection created?",
    "How is the project indexed?",
    "Where is the reranker implemented?",
    "Which file handles tool registration?",
]

GIT_QUESTIONS = [
    "What was the latest commit?",
    "Show me the git diff",
    "What changed recently?",
    "Show git status",
    "What is new in this project?",
]

ACTION_QUESTIONS = [
    "Add input validation to app/api.py",
    "Fix the bug in the search module",
    "Implement a new tool for listing files",
    "Refactor the context builder",
    "Update the README with new instructions",
]

READ_ONLY_QUESTIONS = [
    "Where is hybrid search implemented?",
    "Explain the agent loop",
    "Describe the indexing pipeline",
    "What does the reranker do?",
    "Show me the tool registry",
]


@pytest.mark.parametrize("question", SEARCH_QUESTIONS)
def test_search_questions_route_to_code_search(question):
    assert task_requires_code_search(question), (
        f"Expected code search routing for: {question!r}"
    )


@pytest.mark.parametrize("question", GIT_QUESTIONS)
def test_git_questions_route_to_git_tools(question):
    assert task_requires_git_tools(question), (
        f"Expected git tool routing for: {question!r}"
    )


@pytest.mark.parametrize("question", READ_ONLY_QUESTIONS)
def test_read_only_questions_do_not_allow_writes(question):
    assert task_is_read_only(question), (
        f"Expected read-only routing for: {question!r}"
    )


@pytest.mark.parametrize("question", ACTION_QUESTIONS)
def test_action_questions_are_not_read_only(question):
    assert not task_is_read_only(question), (
        f"Expected write permission for: {question!r}"
    )


# ---------------------------------------------------------------------------
# Tool set correctness
# ---------------------------------------------------------------------------

def test_search_question_exposes_no_write_tools():
    tools = _tools_for_task(False, True, "Where is hybrid search implemented?")
    # retrieval_task=True, git_task=False → empty tool list (context-only)
    assert tools == []


def test_git_question_exposes_only_git_tools():
    names = {t["function"]["name"] for t in _tools_for_task(True, False, "show git status")}
    assert names == {"git_status", "git_diff", "git_log"}


def test_changelog_question_exposes_changelog_tools():
    names = {t["function"]["name"] for t in _tools_for_task(True, False, "update CHANGELOG")}
    assert "patch_file" in names
    assert "git_log" in names


def test_resume_question_exposes_search_and_read():
    names = {t["function"]["name"] for t in _tools_for_task(True, False, "resume from git diff")}
    assert "search_code" in names
    assert "read_file" in names


# ---------------------------------------------------------------------------
# Citation / hallucination detection
# ---------------------------------------------------------------------------

def test_citation_present_and_supported():
    result = verify_evidence_citations(
        "The search is in [app/indexer/search.py#chunk=0].",
        {"app/indexer/search.py#chunk=0"},
        require_citation=True,
    )
    assert result.passed


def test_citation_absent_triggers_retry_flag():
    result = verify_evidence_citations(
        "The search is implemented somewhere.",
        {"app/indexer/search.py#chunk=0"},
        require_citation=True,
    )
    assert not result.passed
    assert result.should_retry


def test_unsupported_citation_triggers_retry_flag():
    result = verify_evidence_citations(
        "See [src/app/core/agents/search.py#chunk=0].",
        {"app/indexer/search.py#chunk=0"},
        require_citation=True,
    )
    assert not result.passed
    assert result.should_retry


def test_fake_narration_detected():
    result = detect_fake_narration("I'm checking the filesystem for the file...")
    assert not result.passed
    assert result.should_retry


def test_fake_narration_let_me():
    result = detect_fake_narration("Let me search the codebase for that function.")
    assert not result.passed


def test_no_fake_narration_in_clean_answer():
    result = detect_fake_narration(
        "The hybrid search is implemented in app/indexer/search.py."
    )
    assert result.passed


# ---------------------------------------------------------------------------
# Path validation (hallucinated paths)
# ---------------------------------------------------------------------------

def test_existing_path_passes_validation(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "router.py").write_text("# router")
    result = validate_mentioned_paths(
        "The router is in app/router.py.",
        tmp_path,
    )
    assert result.passed


def test_nonexistent_path_fails_validation(tmp_path):
    result = validate_mentioned_paths(
        "The router is in src/app/core/agents/search.py.",
        tmp_path,
    )
    assert not result.passed
    assert result.should_retry
    assert "src/app/core/agents/search.py" in result.message


# ---------------------------------------------------------------------------
# Context builder — token-aware budget
# ---------------------------------------------------------------------------

def test_context_builder_respects_token_budget():
    builder = ContextBuilder(model_context_tokens=4096)
    # Budget = (4096 - 1500 - 800 - 2000 - 1024) * 4 = -1228 → clamped to 2000
    assert builder.max_chars >= 2000


def test_context_builder_emits_citations():
    builder = ContextBuilder()
    context = builder.build([{
        "path": "app/indexer/search.py",
        "chunk_index": 0,
        "score": 0.9,
        "content": "def search(): pass",
    }])
    assert "[app/indexer/search.py#chunk=0]" in context


def test_context_builder_filters_low_score():
    builder = ContextBuilder(score_threshold=0.5)
    context = builder.build([{
        "path": "app/indexer/search.py",
        "chunk_index": 0,
        "score": 0.1,
        "content": "def search(): pass",
    }])
    assert context == ""


# ---------------------------------------------------------------------------
# Reranker — symbol/filename matching
# ---------------------------------------------------------------------------

def test_reranker_prefers_exact_function_name():
    results = rerank(
        "def route_request",
        [
            {"path": "app/other.py", "content": "def handle(): pass", "score": 0.95, "chunk_index": 0},
            {"path": "app/router.py", "content": "def route_request(): pass", "score": 0.70, "chunk_index": 0},
        ],
        limit=2,
    )
    assert results[0]["path"] == "app/router.py"


def test_reranker_prefers_filename_match():
    results = rerank(
        "search module",
        [
            # Higher base score but content has no query terms and path doesn't match
            {"path": "app/other.py", "content": "unrelated logic here", "score": 0.80, "chunk_index": 0},
            # Lower base score but filename matches the query
            {"path": "app/search.py", "content": "some content", "score": 0.75, "chunk_index": 0},
        ],
        limit=2,
    )
    assert results[0]["path"] == "app/search.py"


def test_reranker_proximity_bonus_for_early_chunks():
    results = rerank(
        "config",
        [
            {"path": "app/config.py", "content": "config settings", "score": 0.70, "chunk_index": 5},
            {"path": "app/config.py", "content": "config settings", "score": 0.70, "chunk_index": 0},
        ],
        limit=2,
    )
    assert results[0]["chunk_index"] == 0


# ---------------------------------------------------------------------------
# Search integration (in-memory DB)
# ---------------------------------------------------------------------------

def test_search_returns_most_relevant_chunk(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    initialize(db_path)

    with sqlite3.connect(db_path) as db:
        save_chunk(db, "app/indexer/search.py", 0, "def search(db_path, query): pass", [1.0, 0.0])
        save_chunk(db, "app/tools/git.py", 0, "def git_log(): pass", [0.0, 1.0])

    monkeypatch.setattr("app.indexer.search.embed", lambda _: [1.0, 0.0])

    results = search(db_path, "search function", limit=2)
    assert results[0]["path"] == "app/indexer/search.py"


def test_search_no_results_for_empty_index(tmp_path, monkeypatch):
    db_path = tmp_path / "index.db"
    initialize(db_path)
    monkeypatch.setattr("app.indexer.search.embed", lambda _: [1.0, 0.0])
    results = search(db_path, "anything", limit=5)
    assert results == []


# ---------------------------------------------------------------------------
# Intent routing edge cases
# ---------------------------------------------------------------------------

def test_changelog_intent_detected():
    assert task_is_changelog_request("update CHANGELOG from the diff")
    assert task_is_changelog_request("add entry to change log")


def test_resume_intent_detected():
    assert task_is_resume_request("resume from git diff")
    assert task_is_resume_request("continue from git diff")


def test_commit_message_intent_detected():
    assert task_is_commit_message_request("create a commit message")
    assert task_is_commit_message_request("write commit messages for these changes")
