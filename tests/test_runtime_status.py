from io import StringIO
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient
from rich.console import Console

from app import cli
from app.agent.core import Agent
from app.api import create_app
from app.llm.client import LLMClient
from app.service import AgentService


METADATA = {
    "capabilities": ["completion", "tools"],
    "model_info": {"general.architecture": "llama", "llama.context_length": 32768},
}
RUNTIME = {
    "model": "server-model",
    "context_budget_tokens": 8192,
    "evidence_max_chars": 11472,
    "max_output_tokens": 512,
    "capabilities": ["completion", "tools"],
    "model_context_tokens": 32768,
}


def client_with_response(monkeypatch, data=METADATA):
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/proxy/v1/")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    client = LLMClient()
    client.session = Mock()
    client.session.post.return_value.json.return_value = data
    return client


def test_metadata_uses_chat_host_and_current_model_without_generation(monkeypatch):
    client = client_with_response(monkeypatch)
    assert client.model_metadata() == {
        "capabilities": ["completion", "tools"], "model_context_tokens": 32768,
    }
    client.session.post.assert_called_once_with(
        "http://localhost:11434/proxy/api/show", json={"model": "test-model"}, timeout=2,
    )
    monkeypatch.setenv("LLM_MODEL", "second-model")
    client.model_metadata()
    assert client.session.post.call_args.kwargs["json"] == {"model": "second-model"}


@pytest.mark.parametrize("failure", [requests.Timeout(), requests.ConnectionError(),
                                   requests.HTTPError(), ValueError("invalid JSON")])
def test_metadata_failure_keeps_diagnostics_available(monkeypatch, failure):
    client = client_with_response(monkeypatch)
    client.session.post.side_effect = failure
    assert client.model_metadata() == {"capabilities": None, "model_context_tokens": None}


@pytest.mark.parametrize("data", [None, [], {}, {"capabilities": "tools"},
                                  {"capabilities": [None]}, {"model_info": []},
                                  {"model_info": {"general.architecture": "llama",
                                                  "llama.context_length": True}}])
def test_missing_or_invalid_metadata_is_unknown(monkeypatch, data):
    assert client_with_response(monkeypatch, data).model_metadata() == {
        "capabilities": None, "model_context_tokens": None,
    }


def test_empty_capabilities_are_distinct_from_unknown(monkeypatch):
    assert client_with_response(monkeypatch, {"capabilities": []}).model_metadata() == {
        "capabilities": [], "model_context_tokens": None,
    }


def test_status_reports_active_context_and_dynamic_output_budget(monkeypatch, tmp_path):
    monkeypatch.setattr(Agent, "_load_history", lambda self: None)
    monkeypatch.setenv("OWA_CONTEXT_TOKENS", "4096")
    monkeypatch.setenv("OWA_MAX_OUTPUT_TOKENS", "999999")
    agent = Agent()
    monkeypatch.setattr(agent.llm, "model_metadata", lambda: {
        "capabilities": None, "model_context_tokens": None,
    })
    # ContextBuilder is created once; diagnostics must reflect its active budget.
    monkeypatch.setenv("OWA_CONTEXT_TOKENS", "8192")
    status = AgentService(tmp_path, agent).status()
    assert status["ready"] is False
    assert status["runtime"]["context_budget_tokens"] == 4096
    assert status["runtime"]["evidence_max_chars"] == 2000
    assert status["runtime"]["max_output_tokens"] == 16384
    monkeypatch.setenv("OWA_MAX_OUTPUT_TOKENS", "512")
    assert agent.runtime_status()["max_output_tokens"] == 512


def test_api_status_preserves_server_runtime_metadata():
    service = Mock()
    service.status.return_value = {"ready": False, "chunks": 0, "runtime": RUNTIME}
    with TestClient(create_app(service, api_key="secret")) as client:
        assert client.get("/status").status_code == 401
        response = client.get("/status", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert response.json() == service.status.return_value


@pytest.mark.parametrize("api_mode", [False, True])
def test_startup_and_status_use_service_runtime(monkeypatch, api_mode):
    service = Mock()
    service.status.return_value = {"ready": True, "chunks": 3, "runtime": RUNTIME}
    monkeypatch.setattr(cli, "AgentService", lambda: service)
    monkeypatch.setattr(cli, "ApiClient", lambda *args: service)
    monkeypatch.setattr(cli, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("LLM_MODEL", "wrong-local-model")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setattr(cli.Prompt, "ask", Mock(side_effect=["/status", "/quit"]))
    output = StringIO()
    monkeypatch.setattr(cli, "console", Console(file=output, theme=cli.THEME, width=180))
    cli.main(["--api-url", "http://server"] if api_mode else [])
    rendered = output.getvalue()
    assert rendered.count("server-model") == 2
    assert "wrong-local-model" not in rendered
    assert "output limit: 512 tokens" in rendered
    assert "model max context: 32768" in rendered
    if api_mode:
        assert "No config found" not in rendered
    service.index.assert_not_called()


def test_status_handles_old_server_and_unknown_metadata(monkeypatch):
    output = StringIO()
    monkeypatch.setattr(cli, "console", Console(file=output, theme=cli.THEME, width=180))
    cli.print_status({"ready": False, "chunks": 0})
    cli.print_status({"ready": False, "chunks": 0, "runtime": {
        **RUNTIME, "capabilities": None, "model_context_tokens": None,
    }})
    assert "Runtime diagnostics unavailable" in output.getvalue()
    assert "capabilities: unknown" in output.getvalue()
    assert "model max context: unknown" in output.getvalue()


def test_metadata_outage_does_not_prevent_chat(monkeypatch):
    client = client_with_response(monkeypatch)
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
    client.session.post.side_effect = [requests.Timeout(), response]
    assert client.model_metadata()["capabilities"] is None
    assert client.chat([]) == response.json.return_value
