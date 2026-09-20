from copy import deepcopy

import pytest

from app.agent.core import (
    Agent, SYSTEM_PROMPT, _tools_for_task, task_is_conversational,
    task_is_read_only, task_requires_code_search,
)
from app.agent.verifier import verify_tool_result
from app.tools.calls import parse_text_tool_call


def response(content=None, tool=None, arguments="{}"):
    message = {"content": content}
    if tool:
        message["tool_calls"] = [{"id": "call-1", "type": "function",
                                  "function": {"name": tool, "arguments": arguments}}]
    return {"choices": [{"message": message}]}


@pytest.mark.parametrize("streaming", [False, True])
def test_current_evidence_reaches_model_and_previous_evidence_is_removed(monkeypatch, streaming):
    agent = Agent()
    agent.messages.append({"role": "system", "content": "STALE EVIDENCE"})
    monkeypatch.setattr(agent, "_build_search_context", lambda _: "CURRENT EVIDENCE")
    captured = []

    def chat(messages, tools=None):
        captured.extend(deepcopy(messages))
        return response("No matching implementation.")

    def stream(messages):
        captured.extend(deepcopy(messages))
        yield "No matching implementation."

    monkeypatch.setattr(agent.llm, "chat", chat)
    monkeypatch.setattr(agent.llm, "chat_stream", stream)
    list(agent.stream("Where is the router?")) if streaming else agent.run("Where is the router?")
    prompt = "\n".join(m.get("content", "") for m in captured)
    assert "CURRENT EVIDENCE" in prompt
    assert "STALE EVIDENCE" not in prompt
    assert "RESPONSE MODE: location_question" in prompt
    assert "CONTEXT ISOLATION RULE" in prompt


@pytest.mark.parametrize("streaming", [False, True])
def test_greeting_does_not_resume_history_or_offer_tools(monkeypatch, streaming):
    agent = Agent()
    agent.messages += [{"role": "user", "content": "Read all markdown files"},
                       {"role": "assistant", "content": "python3 - old unrelated script"}]

    def check(messages):
        assert len(messages) == 2
        assert messages[-1] == {"role": "user", "content": "hello"}
        assert "old unrelated script" not in str(messages)

    def chat(messages, tools=None):
        check(messages)
        assert tools == []
        return response("Hello!")

    def stream(messages):
        check(messages)
        yield "Hello!"

    monkeypatch.setattr(agent.llm, "chat", chat)
    monkeypatch.setattr(agent.llm, "chat_stream", stream)
    result = "".join(agent.stream("hello")) if streaming else agent.run("hello")
    assert result == "Hello!"
    assert agent.state.tool_calls == 0


def test_streamed_change_executes_tools_and_preserves_verification_instruction(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tools.filesystem.WORKSPACE", tmp_path)
    agent = Agent()
    monkeypatch.setattr(agent, "_build_search_context", lambda _: "")
    calls = []
    answers = iter([
        response(tool="write_file", arguments='{"path":"hello.txt","content":"hello"}'),
        response("Done."),  # Must trigger verification instead of ending the task.
        response(tool="read_file", arguments='{"path":"hello.txt"}'),
        response("Created hello.txt and verified its contents."),
    ])

    def chat(messages, tools=None):
        calls.append(deepcopy(messages))
        assert any(t["function"]["name"] == "write_file" for t in tools)
        assert "Do not use tools or invent" not in str(messages)
        return next(answers)

    monkeypatch.setattr(agent.llm, "chat", chat)
    monkeypatch.setattr(agent.llm, "chat_stream", lambda _: pytest.fail("action sent without tools"))
    assert "verified" in "".join(agent.stream("Create hello.txt containing hello"))
    assert (tmp_path / "hello.txt").read_text() == "hello"
    assert "VERIFICATION REQUIRED" in str(calls[2])
    assert agent.state.verification_done


def test_history_budget_keeps_complete_tool_turns():
    agent = Agent()
    agent.messages = [{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": "old"},
                      {"role": "assistant", "content": "x" * 9000},
                      {"role": "user", "content": "recent"},
                      {"role": "assistant", "content": None, "tool_calls": []},
                      {"role": "tool", "content": "result", "tool_call_id": "1"},
                      {"role": "assistant", "content": "done"}]
    agent._trim_messages()
    assert [m["role"] for m in agent.messages] == ["system", "user", "assistant", "tool", "assistant"]
    assert agent.messages[1]["content"] == "recent"


@pytest.mark.parametrize("task", ["read calculator.py", "inspect files", "review calculator.py"])
def test_short_tool_requests_are_not_small_talk(task):
    assert not task_is_conversational(task)


@pytest.mark.parametrize("task", ["Where is the add function defined?", "How does update work?", "What does remove do?"])
def test_action_named_symbols_remain_read_only_questions(task):
    assert task_is_read_only(task)
    assert task_requires_code_search(task)


def test_fix_with_tests_still_exposes_editing_tools():
    names = {t["function"]["name"] for t in _tools_for_task(
        False, False, "Fix add in calculator.py and run the tests."
    )}
    assert {"read_file", "patch_file", "run_command"} <= names


@pytest.mark.parametrize("content", [
    '{"name":"read_file","arguments":{"path":"calculator.py"}}',
    '```json\n{"name":"read_file","arguments":{"path":"calculator.py"}}\n```',
    '<tool_call>{"name":"read_file","arguments":{"path":"calculator.py"}}</tool_call>',
    '<tool_response>{"name":"read_file","arguments":{"path":"calculator.py"}}</tool_response>',
])
def test_text_tool_calls_execute_through_normal_loop(monkeypatch, content):
    from app.agent import core
    agent = Agent()
    called = []
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda path: called.append(path) or "return a - b")
    answers = iter([response(content), response("Returns a - b.")])

    def chat(messages, tools=None):
        if called:
            assert tools == []
            assert all(m["role"] != "tool" and "tool_calls" not in m for m in messages)
            assert "RESULT from read_file" in messages[-2]["content"]
            assert "TOOL PROTOCOL" in messages[-1]["content"]
            assert "read_file" in messages[-1]["content"]
        return next(answers)

    monkeypatch.setattr(agent.llm, "chat", chat)
    assert "a - b" in "".join(agent.stream("Read calculator.py"))
    assert called == ["calculator.py"]


@pytest.mark.parametrize("content", [
    'Example: {"name":"read_file","arguments":{}}',
    '{"name":"read_file","arguments":{},"comment":"example"}',
    '```python\nprint("hello")\n```',
    '[{"name":"read_file","arguments":{}}]',
    '<tool_response>Ran 1 test. OK</tool_response>',
])
def test_text_tool_parser_does_not_execute_prose_or_code(content):
    assert parse_text_tool_call(content, 1) is None


def test_text_tool_call_cannot_bypass_read_only_tool_allowlist(monkeypatch):
    from app.agent import core
    agent = Agent()
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: pytest.fail("write must be blocked"))
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "return a - b")
    answers = iter([
        response('{"name":"write_file","arguments":{"path":"x","content":"x"}}'),
        response("I cannot modify files for this inspection."),
        response(tool="read_file", arguments='{"path":"calculator.py"}'),
        response("The function returns a - b."),
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    agent.run("Read calculator.py")
    assert not agent.state.files_changed


@pytest.mark.parametrize("tool, result, passed", [
    ("read_file", "error = None", True),
    ("read_file", "File does not exist: missing.py", False),
    ("patch_file", "patch_file failed: old_str not found in file.", False),
    ("run_command", "STDOUT:\n0 errors\nEXIT_CODE=0", True),
    ("run_command", "STDERR:\nFAILED\nEXIT_CODE=1", False),
    ("run_command", "Command rejected by user.", False),
])
def test_verification_uses_tool_status_instead_of_error_word(tool, result, passed):
    assert verify_tool_result(tool, result).passed is passed


def test_successful_test_command_finishes_verification(monkeypatch):
    from app.agent import core
    agent = Agent()
    answers = iter([response(tool="run_command", arguments='{"command":"python -m unittest -q"}'),
                    response("Tests passed.")])
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda command: "EXIT_CODE=0")
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    assert "Tests passed" in "".join(agent.stream("Run the tests"))
    assert agent.state.verification_done


def test_failed_write_is_not_recorded_as_a_change(monkeypatch):
    from app.agent import core
    agent = Agent()
    answers = iter([response(tool="write_file", arguments='{"path":"x","content":"x"}'),
                    response("Unable to write the file.")])
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: "Tool execution error: PermissionError")
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    agent.run("Create x")
    assert not agent.state.files_changed
    assert agent.state.errors


def test_described_actions_are_corrected_instead_of_reported_as_complete(monkeypatch):
    from app.agent import core
    agent = Agent()
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: "Successfully wrote 1 characters to x")
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "x")
    answers = iter([
        response('I will create x. Example: {"name":"write_file","arguments":{"path":"x","content":"x"}}'),
        response('{"name":"write_file","arguments":{"path":"x","content":"x"}}'),
        response(tool="read_file", arguments='{"path":"x"}'),
        response("Created and verified x."),
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    assert "verified" in agent.run("Create x")
    assert agent.state.files_changed == ["x"]
    assert agent.state.completed


def test_repeated_action_narration_stops_without_claiming_completion(monkeypatch):
    agent = Agent()
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: response("I will create x."))
    assert "could not complete" in agent.run("Create x")
    assert agent.state.tool_calls == 0
    assert not agent.state.completed
    assert agent.state.iteration == 3


def test_failed_read_cannot_verify_a_successful_write(monkeypatch):
    from app.agent import core
    agent = Agent()
    monkeypatch.setitem(core.FUNCTIONS, "write_file", lambda **kwargs: "Successfully wrote 1 characters to x")
    reads = iter(["File does not exist: missing", "x"])
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: next(reads))
    answers = iter([
        response(tool="write_file", arguments='{"path":"x","content":"x"}'),
        response(tool="read_file", arguments='{"path":"missing"}'),
        response("Done."),
        response(tool="read_file", arguments='{"path":"x"}'),
        response("Verified x."),
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    assert agent.run("Create x") == "Verified x."
    assert agent.state.tool_calls == 3
    assert agent.state.verification_done
    assert len(agent.state.errors) == 1


def test_read_cannot_turn_a_failed_test_into_successful_verification(monkeypatch):
    from app.agent import core
    agent = Agent()
    results = iter(["EXIT_CODE=1", "EXIT_CODE=0"])
    monkeypatch.setitem(core.FUNCTIONS, "run_command", lambda **kwargs: next(results))
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "test source")
    answers = iter([
        response(tool="run_command", arguments='{"command":"python -m unittest -q"}'),
        response(tool="read_file", arguments='{"path":"test.py"}'),
        response("Tests passed."),
        response(tool="run_command", arguments='{"command":"python -m unittest -q"}'),
        response("Tests now pass."),
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    assert agent.run("Run the tests") == "Tests now pass."
    assert agent.state.commands_run == ["python -m unittest -q"] * 2
    assert agent.state.verification_done


def test_repeated_tool_failure_stops_with_the_actual_error(monkeypatch):
    from app.agent import core
    agent = Agent()
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "File does not exist: missing.py")
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: response(
        tool="read_file", arguments='{"path":"missing.py"}',
    ))
    result = agent.run("Read missing.py")
    assert "repeated failure in read_file" in result
    assert "File does not exist" in result
    assert agent.state.tool_calls == 3
    assert not agent.state.completed


def test_text_protocol_has_an_explicit_finish_action(monkeypatch):
    from app.agent import core
    agent = Agent()
    monkeypatch.setitem(core.FUNCTIONS, "read_file", lambda **kwargs: "return a - b")
    answers = iter([
        response('{"name":"read_file","arguments":{"path":"calculator.py"}}'),
        response('{"answer":"The function returns a - b."}'),
    ])
    monkeypatch.setattr(agent.llm, "chat", lambda **kwargs: next(answers))
    assert agent.run("Read calculator.py") == "The function returns a - b."
    assert agent.state.completed
    assert agent.state.tool_calls == 1
