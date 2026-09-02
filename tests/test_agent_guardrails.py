from pathlib import Path

import pytest

from app.agent.core import (
    SYSTEM_PROMPT,
    WORKSPACE,
    _tools_for_task,
    task_is_changelog_request,
    task_is_commit_message_request,
    task_is_resume_request,
    task_is_read_only,
    task_requires_code_search,
    task_requires_git_tools,
)
from app.agent.state import AgentState
from app.tools.filesystem import resolve_path
from app.tools.registry import TOOLS
from app.tools.shell import run_command


def test_resolve_path_rejects_absolute_and_escaping_paths():
    with pytest.raises(PermissionError):
        resolve_path("/etc/passwd")

    with pytest.raises(PermissionError):
        resolve_path("../../etc/passwd")

    expected = (WORKSPACE / "app" / "calculator.py").resolve()
    assert resolve_path("app/calculator.py") == expected


def test_system_prompt_mentions_actual_workspace_root():
    assert "WORKSPACE ROOT:" in SYSTEM_PROMPT
    assert str(WORKSPACE) in SYSTEM_PROMPT


def test_read_only_task_detection_blocks_questions_but_allows_explicit_actions():
    assert task_is_read_only(
        "Where is tool execution implemented?"
    )
    assert task_is_read_only("Check the current setup")
    assert not task_is_read_only("Implement the search policy")
    assert not task_is_read_only("Run the test suite")


def test_code_questions_require_search_then_file_verification():
    assert task_requires_code_search(
        "Where is tool execution implemented?"
    )
    assert task_requires_code_search("How does the agent execute commands?")
    assert not task_requires_code_search("Check the current setup")
    assert not task_requires_code_search("Implement the search policy")


def test_repository_phrasing_requires_search_and_disables_tools():
    assert task_requires_code_search(
        "According to this repository, what is the Redis caching architecture?"
    )


def test_git_history_questions_use_git_tools():
    assert task_requires_git_tools(
        "what ever. can u check, last commit? what is new of this project/repo?"
    )
    assert task_requires_git_tools("show the latest commit")


def test_changelog_and_resume_requests_have_dedicated_intents():
    assert task_is_changelog_request("update CHANGELOG from the diff")
    assert task_is_resume_request("resume from git diff")
    assert task_requires_git_tools("update CHANGELOG from the diff")
    assert task_is_commit_message_request("create a commit message")


def test_git_history_routing_exposes_git_tools_without_filesystem_tools():
    names = {
        tool["function"]["name"]
        for tool in _tools_for_task(True, True, "show the latest commit")
    }

    assert names == {"git_status", "git_diff", "git_log"}


def test_mixed_git_and_code_question_exposes_search_tools():
    names = {
        tool["function"]["name"]
        for tool in _tools_for_task(
            True,
            True,
            "what changed in the implementation of the search architecture?",
        )
    }

    assert "git_log" in names
    assert "search_code" in names
    assert "read_file" in names


def test_changelog_update_allows_only_changelog_patch_tools():
    names = {
        tool["function"]["name"]
        for tool in _tools_for_task(True, False, "update CHANGELOG")
    }

    assert names == {"git_status", "git_diff", "git_log", "read_file", "patch_file"}


def test_resume_workflow_allows_relevant_read_tools():
    names = {
        tool["function"]["name"]
        for tool in _tools_for_task(True, False, "resume from git diff")
    }

    assert names == {"git_status", "git_diff", "git_log", "read_file", "search_code"}


def test_system_prompt_requires_retrieved_context_and_read_only_questions():
    assert "client retrieves relevant repository" in SYSTEM_PROMPT
    assert "semantic search -> context builder -> answer" in SYSTEM_PROMPT
    assert "DO NOT write files" in SYSTEM_PROMPT
    assert "DO NOT fix anything unless explicitly requested." in SYSTEM_PROMPT
    assert "DO NOT create tests unless explicitly requested." in SYSTEM_PROMPT


def test_missing_repository_evidence_forbids_invention_and_tools():
    from app.agent.core import _repository_context_message

    message = _repository_context_message("")

    assert "No relevant repository evidence was found" in message
    assert "Do not use tools or invent" in message
    assert "could not verify" in message


def test_repository_context_requires_explicit_evidence():
    from app.agent.core import _repository_context_message

    message = _repository_context_message("FILE: app/api.py\nCONTENT: FastAPI app")

    assert "directly supported by this context" in message
    assert "could not verify it" in message
    assert "Do not explore the filesystem" in message


def test_evidence_verifier_requires_supported_citations():
    from app.agent.verifier import verify_evidence_citations

    supported = verify_evidence_citations(
        "The router is here [app/router.py#chunk=0].",
        {"app/router.py#chunk=0"},
        require_citation=True,
    )
    unsupported = verify_evidence_citations(
        "Redis is configured here [config.py#chunk=2].",
        {"app/router.py#chunk=0"},
        require_citation=True,
    )

    assert supported.passed
    assert not unsupported.passed


def test_context_builder_emits_stable_citations():
    from app.agent.context import ContextBuilder

    context = ContextBuilder().build(
        [{
            "path": "app/router.py",
            "chunk_index": 0,
            "score": 0.9,
            "content": "def route_request(): pass",
        }]
    )

    assert "[app/router.py#chunk=0]" in context


def test_tool_descriptions_prioritize_search_and_protect_writes():
    descriptions = {
        tool["function"]["name"]: tool["function"]["description"]
        for tool in TOOLS
    }

    assert "use this tool FIRST" in descriptions["search_code"]
    assert "does not modify files" in descriptions["search_code"]
    assert "ONLY when the user explicitly requests" in descriptions["write_file"]
    assert "Do not use for ordinary code questions" in descriptions["run_command"]


def test_agent_state_is_per_task_and_has_no_hardcoded_requirements():
    state_a = AgentState(task="Create calculator")
    state_b = AgentState(task="Read /etc/passwd")

    assert state_a.task == "Create calculator"
    assert state_b.task == "Read /etc/passwd"
    assert state_a is not state_b
    assert not hasattr(state_a, "requirements")
    assert not hasattr(state_b, "requirements")


def test_run_command_rejects_absolute_and_escape_paths(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_args, **_kwargs: "y")

    blocked = run_command("ls /etc/passwd")
    assert "outside workspace" in blocked.lower()

    blocked = run_command("ls ../../etc/passwd")
    assert "outside workspace" in blocked.lower()

    allowed = run_command("pwd")
    assert str(WORKSPACE) in allowed


def test_run_command_handles_missing_stdin_gracefully(monkeypatch):
    def raise_eof(*_args, **_kwargs):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)

    result = run_command("pwd")
    assert "Command rejected by user." in result
