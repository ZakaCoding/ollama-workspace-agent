import copy
from unittest.mock import Mock

import pytest

from app.agent.core import Agent
from app.tools.registry import TOOLS
from app.tools.validation import validate_arguments


def schema(name):
    return next(t["function"]["parameters"] for t in TOOLS
                if t["function"]["name"] == name)


@pytest.mark.parametrize("raw, error", [
    ('{"path":', "valid JSON"),
    ('null', "JSON object"),
    ('[]', "JSON object"),
    ('42', "JSON object"),
    ('"file.py"', "JSON object"),
    (None, "JSON object"),
    ({}, "missing required"),
    ({"path": None}, "type string"),
    ({"path": ["file.py"]}, "type string"),
    ({"path": "file.py", "extra": True}, "unexpected arguments"),
])
def test_rejects_invalid_arguments(raw, error):
    with pytest.raises(ValueError, match=error):
        validate_arguments(raw, schema("read_file"))


@pytest.mark.parametrize("limit", [True, False, "5", 5.5, None, [], {}])
def test_integer_arguments_are_not_coerced(limit):
    with pytest.raises(ValueError, match="type integer"):
        validate_arguments({"query": "agent", "limit": limit}, schema("search_code"))


@pytest.mark.parametrize("name, raw, expected", [
    ("list_dir", "{}", {}),
    ("git_status", {}, {}),
    ("read_file", '{"path":"file.py"}', {"path": "file.py"}),
    ("search_code", {"query": "agent"}, {"query": "agent"}),
    ("search_code", {"query": "agent", "limit": 3}, {"query": "agent", "limit": 3}),
    ("patch_file", {"path": "a", "old_str": "x", "new_str": ""},
     {"path": "a", "old_str": "x", "new_str": ""}),
])
def test_valid_arguments_preserve_optional_defaults_and_empty_strings(name, raw, expected):
    assert validate_arguments(raw, schema(name)) == expected


def call(name, arguments, call_id="call_1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": arguments}}


@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setattr(Agent, "_load_history", lambda self: None)
    monkeypatch.setattr(Agent, "_save_history", lambda self: None)
    monkeypatch.setattr(Agent, "_build_search_context", lambda self, task: "")
    return Agent()


def replies(agent, messages):
    snapshots = []
    iterator = iter(messages)

    def chat(**kwargs):
        snapshots.append(copy.deepcopy(kwargs))
        return {"choices": [{"message": next(iterator)}]}

    agent.llm.chat = chat
    return snapshots


def test_invalid_write_recovers_without_side_effects_or_false_state(agent, monkeypatch):
    from app.agent import core

    write = Mock(return_value="Successfully wrote 2 characters to a.txt")
    read = Mock(return_value="ok")
    monkeypatch.setitem(core.FUNCTIONS, "write_file", write)
    monkeypatch.setitem(core.FUNCTIONS, "read_file", read)
    snapshots = replies(agent, [
        {"tool_calls": [call("write_file", {"path": "a.txt", "content": None})]},
        {"tool_calls": [call("write_file", {"path": "a.txt", "content": "ok"}, "call_2")]},
        {"tool_calls": [call("read_file", {"path": "a.txt"}, "call_3")]},
        {"content": "Done."},
    ])
    assert agent.run("Create a.txt") == "Done."
    write.assert_called_once_with(path="a.txt", content="ok")
    read.assert_called_once_with(path="a.txt")
    error = snapshots[1]["messages"][-1]
    assert error["role"] == "tool"
    assert error["tool_call_id"] == "call_1"
    assert "Retry with corrected arguments" in error["content"]
    assert agent.state.files_changed == ["a.txt"]
    assert agent.state.tool_calls == 3
    assert len(agent.state.errors) == 1
    assert agent.state.verification_done


def test_repeated_invalid_calls_stop_at_iteration_budget(agent, monkeypatch):
    from app.agent import core

    write = Mock()
    monkeypatch.setitem(core.FUNCTIONS, "write_file", write)
    replies(agent, [{"tool_calls": [call("write_file", "null")]}] * 20)
    assert agent.run("Create a.txt") == "Agent reached maximum iterations."
    write.assert_not_called()
    assert not agent.state.files_changed
    assert not agent.state.verification_required
    assert not agent.state.completed
    assert len(agent.state.errors) == 20


def test_mixed_batch_keeps_valid_calls_and_focused_tools(agent, monkeypatch):
    from app.agent import core

    status = Mock(return_value="clean")
    write = Mock()
    monkeypatch.setitem(core.FUNCTIONS, "git_status", status)
    monkeypatch.setitem(core.FUNCTIONS, "write_file", write)
    snapshots = replies(agent, [
        {"tool_calls": [call("git_status", {"extra": True}),
                        call("write_file", {"path": "a", "content": "x"}, "call_2"),
                        call("git_status", {}, "call_3")]},
        {"content": "Working tree is clean."},
    ])
    assert agent.run("show the latest commit") == "Working tree is clean."
    status.assert_called_once_with()
    write.assert_not_called()
    for snapshot in snapshots:
        assert {t["function"]["name"] for t in snapshot["tools"]} == {
            "git_status", "git_diff", "git_log"}
    results = [m for m in snapshots[1]["messages"] if m["role"] == "tool"]
    assert {m["tool_call_id"] for m in results} == {"call_1", "call_2", "call_3"}


def test_validated_arguments_still_enforce_workspace_boundary(agent, monkeypatch, tmp_path):
    from app.tools import filesystem

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setattr(filesystem, "WORKSPACE", workspace)
    snapshots = replies(agent, [
        {"tool_calls": [call("write_file", {"path": "../outside.txt", "content": "x"})]},
        {"tool_calls": [call("read_file", {"path": "missing.txt"}, "call_2")]},
        {"content": "Unable to write outside the workspace."},
    ])
    agent.run("Create a file")
    assert not (tmp_path / "outside.txt").exists()
    assert "PermissionError" in snapshots[1]["messages"][-1]["content"]
