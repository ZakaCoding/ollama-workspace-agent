import pytest

from app.agent.core import (
    Agent, _tools_for_task, task_is_read_only,
    task_requires_code_search, task_requires_git_tools,
)


@pytest.fixture(autouse=True)
def isolate_routing_search(monkeypatch):
    """Routing tests use stubbed tools and must not query the live index server."""
    monkeypatch.setattr("app.agent.core.search", lambda *args, **kwargs: [])


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


def test_initial_command_must_run_before_requested_fix(monkeypatch):
    from app.agent import core

    agent = Agent()
    executed = []
    results = iter(["EXIT_CODE=1", "EXIT_CODE=0"])
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: executed.append("run") or next(results))
    monkeypatch.setitem(core.FUNCTIONS, "patch_file", lambda **kwargs: executed.append("patch") or "Patched calculator.py")
    patch = {"name": "patch_file", "arguments": {"path": "calculator.py", "old_str": "a - b", "new_str": "a + b"}}
    command = {"name": "run_command", "arguments": {"command": "python -m unittest -q"}}
    replies = iter([patch, command, patch, command, None])

    def chat(messages, tools=None):
        if not executed:
            assert "patch_file" not in {tool["function"]["name"] for tool in tools}
        call = next(replies)
        message = {"tool_calls": [{"id": "call", "type": "function", "function": call}]} if call else {"content": "Fixed and verified."}
        return {"choices": [{"message": message}]}

    monkeypatch.setattr(agent.llm, "chat", chat)
    assert agent.run("Run python -m unittest -q and fix any failures") == "Fixed and verified."
    assert executed == ["run", "patch", "run"]


def test_agent_normalizes_only_in_workspace_absolute_paths(tmp_path, monkeypatch):
    from app.agent import core

    monkeypatch.setattr(core, "WORKSPACE", tmp_path)
    agent = Agent()
    paths = []
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda path: paths.append(path) or "source")
    replies = iter([
        {"tool_calls": [{"id": "outside", "type": "function", "function": {
            "name": "read_file", "arguments": {"path": str(tmp_path.parent / "outside.py")},
        }}]},
        {"tool_calls": [{"id": "inside", "type": "function", "function": {
            "name": "read_file", "arguments": {"path": str(tmp_path / "hello.py")},
        }}]},
        {"content": "Read the source."},
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: {"choices": [{"message": next(replies)}]})
    agent.run("Read hello.py")
    assert paths == ["hello.py"]
    assert len(agent.state.errors) == 1


def test_absolute_path_normalization_rejects_symlink_escape(tmp_path):
    from app.tools.validation import normalize_workspace_arguments

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="inside the workspace"):
        normalize_workspace_arguments("write_file", {
            "path": str(workspace / "link" / "secret.txt"), "content": "changed",
        }, workspace)
    assert not (outside / "secret.txt").exists()
