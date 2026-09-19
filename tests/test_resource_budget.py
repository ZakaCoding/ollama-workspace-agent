from app.agent.context import ContextBuilder
from app.config import context_window_tokens, max_output_tokens
from app.llm.client import LLMClient


def test_context_budget_reads_environment(monkeypatch):
    monkeypatch.setenv("OWA_CONTEXT_TOKENS", "4096")

    assert context_window_tokens() == 4096
    assert ContextBuilder().max_chars == 2000


def test_resource_settings_fall_back_and_clamp(monkeypatch):
    monkeypatch.setenv("OWA_CONTEXT_TOKENS", "not-an-integer")
    monkeypatch.setenv("OWA_MAX_OUTPUT_TOKENS", "999999")

    assert context_window_tokens() == 8192
    assert max_output_tokens() == 16384


def test_llm_requests_include_output_budget(monkeypatch):
    monkeypatch.setenv("OWA_MAX_OUTPUT_TOKENS", "512")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeSession:
        def post(self, *args, **kwargs):
            self.kwargs = kwargs
            return FakeResponse()

    client = LLMClient()
    client.session = FakeSession()
    client.chat([{"role": "user", "content": "hello"}])

    assert client.session.kwargs["json"]["max_tokens"] == 512
