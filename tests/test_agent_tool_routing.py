import pytest

from app.agent.core import (
    Agent, _tools_for_task, task_is_read_only,
    task_requires_code_search, task_requires_git_tools,
)


@pytest.mark.parametrize("task, required", [
    ("List files in the current directory using list_dir.", {"list_dir"}),
    ("Show calculator.py using read_file.", {"read_file"}),
    ("Run python -c 'print(42)'", {"run_command"}),
    ("can u fix calculator.py and run tests", {"patch_file", "run_command"}),
    ("I need you to update calculator.py", {"patch_file"}),
    ("Check git status and fix calculator.py", {"git_status", "patch_file", "run_command"}),
    ("Use run_command to execute python --version", {"run_command"}),
    ("Review unsafe.py using code_review", {"code_review"}),
    ("Find add using search_code", {"search_code"}),
    ("Fix calculator.py and use git_diff", {"patch_file", "git_diff"}),
])
def test_direct_requests_expose_needed_tools(task, required):
    assert not task_requires_code_search(task)
    names = {tool["function"]["name"] for tool in _tools_for_task(
        task_requires_git_tools(task), task_requires_code_search(task), task,
    )}
    assert names >= required


@pytest.mark.parametrize("task", [
    "How does run_command work?", "Where is the add function?",
    "Read calculator.py and explain the bug. Do not fix it or run commands.",
    "Can you explain how to use write_file?", "Do not run tests.",
    "Review unsafe.py using code_review. Do not edit it.",
])
def test_read_only_language_does_not_authorize_writes(task):
    assert task_is_read_only(task)


def test_direct_command_does_not_finish_without_execution(monkeypatch):
    from app.agent import core

    agent = Agent()
    calls = []
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: calls.append(kwargs) or "STDOUT:\n42\nEXIT_CODE=0")
    replies = iter([
        {"content": "The output is 42."},
        {"content": None, "tool_calls": [{"id": "call1", "type": "function", "function": {
            "name": "run_command", "arguments": {"command": 'python -c "print(6 * 7)"'},
        }}]},
        {"content": "The output is 42."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    assert agent.run('Run python -c "print(6 * 7)"') == "The output is 42."
    assert len(calls) == 1
    assert agent.state.completed


def test_requested_tests_cannot_be_replaced_by_readback(monkeypatch):
    from app.agent import core

    agent = Agent()
    calls = []
    monkeypatch.setitem(core.FUNCTIONS, "patch_file", lambda **kwargs: "Patched calculator.py: replaced 1 occurrence.")
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "return a + b")
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: calls.append(kwargs) or "EXIT_CODE=0")

    def call(name, arguments):
        return {"tool_calls": [{"id": name, "type": "function", "function": {
            "name": name, "arguments": arguments,
        }}]}

    replies = iter([
        call("patch_file", {"path": "calculator.py", "old_str": "a - b", "new_str": "a + b"}),
        call("read_file", {"path": "calculator.py"}),
        {"content": "Done, tests pass."},
        call("run_command", {"command": "python -m unittest -q"}),
        {"content": "Fixed and tested."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    assert agent.run("Fix calculator.py and run python -m unittest -q") == "Fixed and tested."
    assert len(calls) == 1
