from pathlib import Path

import pytest

from app.agent.core import (
    SYSTEM_PROMPT,
    WORKSPACE,
    task_is_read_only,
    task_requires_code_search,
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


def test_system_prompt_requires_search_first_and_read_only_questions():
    assert "FIRST use search_code" in SYSTEM_PROMPT
    assert "search_code -> read_file -> answer" in SYSTEM_PROMPT
    assert "DO NOT write files" in SYSTEM_PROMPT
    assert "DO NOT fix anything unless explicitly requested." in SYSTEM_PROMPT
    assert "DO NOT create tests unless explicitly requested." in SYSTEM_PROMPT


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
