from pathlib import Path

import pytest

from app.agent.core import SYSTEM_PROMPT, WORKSPACE
from app.agent.state import AgentState
from app.tools.filesystem import resolve_path
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
