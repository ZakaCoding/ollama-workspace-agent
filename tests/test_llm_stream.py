import pytest

from app.llm.client import IncompleteStreamError, LLMClient


class FakeResponse:

    def raise_for_status(self):
        pass

    def iter_lines(self, decode_unicode=True):
        return [
            "data: {\"choices\":[{\"delta\":{\"content\":\"hello\"}}]}",
            "data: {\"choices\":[{\"delta\":{\"content\":\" world\"}}]}",
            "data: [DONE]",
        ]


class FakeSession:

    def post(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return FakeResponse()


def test_chat_stream_parses_openai_compatible_chunks():
    client = LLMClient()
    client.session = FakeSession()

    assert list(client.chat_stream([{"role": "user", "content": "hi"}])) == [
        "hello",
        " world",
    ]
    assert client.session.kwargs["stream"] is True
    assert client.session.kwargs["json"]["stream"] is True


def test_chat_stream_rejects_non_terminal_finish_reason():
    class TruncatedResponse(FakeResponse):
        def iter_lines(self, decode_unicode=True):
            return [
                'data: {"choices":[{"delta":{"content":"partial"},"finish_reason":"length"}]}',
            ]

    class TruncatedSession(FakeSession):
        def post(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            return TruncatedResponse()

    client = LLMClient()
    client.session = TruncatedSession()

    with pytest.raises(IncompleteStreamError):
        list(client.chat_stream([{"role": "user", "content": "hi"}]))


def test_agent_discards_partial_stream_before_fallback(monkeypatch):
    from app.agent.core import Agent

    class FailingStreamLLM:
        def chat_stream(self, _messages):
            yield "partial"
            raise IncompleteStreamError("truncated")

        def chat(self, messages, tools=None):
            return {
                "choices": [
                    {"message": {"content": "complete response"}}
                ]
            }

    agent = Agent()
    agent.llm = FailingStreamLLM()
    monkeypatch.setattr(agent, "_build_search_context", lambda _task: "")

    assert list(agent.stream("Explain this behavior")) == ["complete response"]


def test_agent_yields_complete_stream_response(monkeypatch):
    from app.agent.core import Agent

    class CompleteStreamLLM:
        def chat_stream(self, _messages):
            yield "complete "
            yield "stream"

    agent = Agent()
    agent.llm = CompleteStreamLLM()
    monkeypatch.setattr(agent, "_build_search_context", lambda _task: "")

    assert list(agent.stream("Explain this behavior")) == ["complete stream"]


def test_agent_reports_empty_response_instead_of_silence(monkeypatch):
    from app.agent.core import Agent, NO_RESPONSE_MESSAGE

    class EmptyLLM:
        def chat_stream(self, _messages):
            return
            yield

        def chat(self, _messages, tools=None):
            return {"choices": [{"message": {"content": ""}}]}

    agent = Agent()
    agent.llm = EmptyLLM()
    monkeypatch.setattr(agent, "_build_search_context", lambda _task: "")

    assert list(agent.stream("Explain this behavior")) == [NO_RESPONSE_MESSAGE]


def test_agent_handles_null_content_after_tool_call(monkeypatch):
    from app.agent.core import Agent, NO_RESPONSE_MESSAGE

    class ToolThenNullLLM:
        def __init__(self):
            self.calls = 0

        def chat(self, _messages, tools=None):
            self.calls += 1
            if self.calls == 1:
                return {
                    "choices": [{
                        "message": {
                            "content": None,
                            "tool_calls": [{
                                "id": "call-1",
                                "function": {
                                    "name": "git_log",
                                    "arguments": {},
                                },
                            }],
                        }
                    }]
                }
            return {"choices": [{"message": {"content": None}}]}

    agent = Agent()
    agent.llm = ToolThenNullLLM()
    monkeypatch.setattr(agent, "_save_history", lambda: None)

    assert list(agent.stream("show the latest commit")) == [NO_RESPONSE_MESSAGE]
