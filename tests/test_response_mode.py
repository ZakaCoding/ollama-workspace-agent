"""Tests for response mode classifier and history sanitization."""
import pytest

from app.agent.response_mode import (
    CHANGE_SUMMARY,
    GENERAL_QUESTION,
    LOCATION_QUESTION,
    HISTORY_ISOLATION_RULE,
    classify_response_mode,
    response_mode_contract,
)
from app.agent.core import _is_drifted_message, _sanitize_history


# ── Response mode classifier ──────────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "where is hybrid search implemented?",
    "where are the git tools?",
    "which file handles tool registration?",
    "which files contain FTS5 logic?",
    "find the reranker implementation",
    "what file contains the agent loop?",
])
def test_location_questions_classify_correctly(question):
    assert classify_response_mode(question) == LOCATION_QUESTION


@pytest.mark.parametrize("question", [
    "what changed in the search system?",
    "what has changed recently?",
    "what was modified in the last commit?",
    "which files were modified?",
    "summarize the changes",
    "what is new in this version?",
])
def test_change_summary_questions_classify_correctly(question):
    assert classify_response_mode(question) == CHANGE_SUMMARY


@pytest.mark.parametrize("question", [
    "explain the agent loop",
    "how does indexing work?",
    "describe the reranker",
    "hello",
    "what does OwA do?",
])
def test_general_questions_classify_correctly(question):
    assert classify_response_mode(question) == GENERAL_QUESTION


def test_location_contract_enforces_5_line_limit():
    contract = response_mode_contract("where is hybrid search implemented?")
    assert "5 lines" in contract
    assert "citation" in contract.lower()
    assert "Do NOT mention files" in contract


def test_change_contract_forbids_assessments():
    contract = response_mode_contract("what changed in the search system?")
    assert "assessments" in contract.lower() or "assessment" in contract.lower()
    assert "Do NOT repeat" in contract
    assert "Do NOT invent" in contract


def test_general_contract_forbids_recycled_assessments():
    contract = response_mode_contract("explain the agent loop")
    assert "Do NOT repeat previous conversation assessments" in contract


def test_history_isolation_rule_mentions_version():
    assert "version" in HISTORY_ISOLATION_RULE.lower()
    assert "NOT repository evidence" in HISTORY_ISOLATION_RULE


# ── History sanitization ──────────────────────────────────────────────────────

def test_drifted_honest_assessment_detected():
    msg = {"role": "assistant", "content": "## Honest Assessment of OwA v0.5.7\nThis is drift."}
    assert _is_drifted_message(msg)


def test_drifted_production_readiness_detected():
    msg = {"role": "assistant", "content": "## Production Readiness Issues\nNeeds work."}
    assert _is_drifted_message(msg)


def test_drifted_old_version_detected():
    msg = {"role": "assistant", "content": "OwA v0.3.1 has this feature."}
    assert _is_drifted_message(msg)


def test_drifted_hallucinated_path_detected():
    msg = {"role": "assistant", "content": "See src/app/core/agents/search.py for details."}
    assert _is_drifted_message(msg)


def test_drifted_hallucinated_shell_var_detected():
    msg = {"role": "assistant", "content": "find $(OWA_WORKDIR) -name '*.py'"}
    assert _is_drifted_message(msg)


def test_clean_message_not_flagged():
    msg = {"role": "assistant", "content": "Hybrid search is in app/indexer/search.py [app/indexer/search.py#chunk=0]."}
    assert not _is_drifted_message(msg)


def test_user_message_never_flagged():
    msg = {"role": "user", "content": "Honest Assessment of OwA v0.5.7"}
    assert not _is_drifted_message(msg)


def test_sanitize_removes_drifted_messages():
    history = [
        {"role": "user", "content": "where is hybrid search?"},
        {"role": "assistant", "content": "## Honest Assessment of OwA v0.5.7\nDrift content."},
        {"role": "user", "content": "what changed?"},
        {"role": "assistant", "content": "The search changed in app/indexer/search.py."},
    ]
    clean = _sanitize_history(history)
    assert len(clean) == 2
    assert clean[0]["content"] == "what changed?"
    assert clean[1]["content"] == "The search changed in app/indexer/search.py."


def test_sanitize_removes_preceding_user_message_of_drifted_response():
    history = [
        {"role": "user", "content": "where is hybrid search?"},
        {"role": "assistant", "content": "## Honest Assessment of OwA v0.5.7\nDrift."},
    ]
    clean = _sanitize_history(history)
    assert clean == []


def test_sanitize_preserves_clean_history():
    history = [
        {"role": "user", "content": "where is hybrid search?"},
        {"role": "assistant", "content": "It is in app/indexer/search.py [app/indexer/search.py#chunk=0]."},
    ]
    clean = _sanitize_history(history)
    assert len(clean) == 2


def test_sanitize_handles_empty_history():
    assert _sanitize_history([]) == []
