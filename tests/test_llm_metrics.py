import json
from io import StringIO
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient
from rich.console import Console

from app import cli
from app.agent.core import Agent
from app.api import create_app
from app.llm.client import IncompleteStreamError, LLMClient
from app.llm.metrics import LLMMetrics
from app.service import AgentService


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "test-model")
    timer = iter([1, 1.25, 2, 2.5, 3, 3.75])
    monkeypatch.setattr("app.llm.client.perf_counter", lambda: next(timer))
    client = LLMClient()
    client.session = Mock()
    return client


def response(usage=None):
    result = Mock()
    result.json.return_value = {
        "choices": [{"message": {"content": "private response"}}], "usage": usage,
    }
    return result


def stream_response(*events):
    result = Mock()
    result.iter_lines.return_value = [
        "data: " + (event if isinstance(event, str) else json.dumps(event))
        for event in events
    ]
    return result


def test_chat_records_latency_and_usage_without_content(client):
    result = response({"prompt_tokens": 12, "completion_tokens": 3})
    client.session.post.return_value = result
    assert client.chat([{"role": "user", "content": "private prompt"}]) == result.json.return_value
    metrics = client.metrics.snapshot()
    assert metrics == {
        "requests": 1, "failed_requests": 0, "total_duration_ms": 250.0,
        "prompt_tokens": 12, "completion_tokens": 3, "requests_with_usage": 1,
        "last_request": {
            "model": "test-model", "streaming": False, "succeeded": True,
            "duration_ms": 250.0, "prompt_tokens": 12, "completion_tokens": 3,
        },
    }
    assert "private" not in json.dumps(metrics)


@pytest.mark.parametrize("usage", [None, {}, [], "invalid",
                                  {"prompt_tokens": True, "completion_tokens": -1},
                                  {"prompt_tokens": "12", "completion_tokens": 1.5}])
def test_missing_or_invalid_usage_is_not_invented(client, usage):
    client.session.post.return_value = response(usage)
    client.chat([])
    metrics = client.metrics.snapshot()
    assert metrics["requests_with_usage"] == 0
    assert metrics["prompt_tokens"] == metrics["completion_tokens"] == 0
    assert metrics["last_request"]["prompt_tokens"] is None
    assert metrics["last_request"]["completion_tokens"] is None


def test_partial_usage_keeps_known_counts_but_not_complete_coverage(client):
    client.session.post.return_value = response({"prompt_tokens": 7})
    client.chat([])
    metrics = client.metrics.snapshot()
    assert metrics["prompt_tokens"] == 7
    assert metrics["requests_with_usage"] == 0
    assert metrics["last_request"]["completion_tokens"] is None


@pytest.mark.parametrize("streaming", [False, True])
def test_network_failure_is_counted_and_preserves_exception(client, streaming):
    client.session.post.side_effect = requests.Timeout("private host info")
    with pytest.raises(requests.Timeout):
        list(client.chat_stream([])) if streaming else client.chat([])
    metrics = client.metrics.snapshot()
    assert metrics["failed_requests"] == 1
    assert metrics["total_duration_ms"] == 250
    assert "private host" not in json.dumps(metrics)


def test_stream_reads_usage_only_event_once_and_closes_response(client):
    usage = {"prompt_tokens": 11, "completion_tokens": 2}
    result = stream_response(
        {"choices": [{"delta": {"content": "hi"}}], "usage": None},
        {"choices": [], "usage": usage},
        {"choices": [], "usage": usage}, "[DONE]",
    )
    client.session.post.return_value = result
    assert list(client.chat_stream([])) == ["hi"]
    assert client.session.post.call_args.kwargs["json"]["stream_options"] == {"include_usage": True}
    metrics = client.metrics.snapshot()
    assert metrics["requests"] == metrics["requests_with_usage"] == 1
    assert metrics["prompt_tokens"] == 11
    assert metrics["completion_tokens"] == 2
    assert metrics["last_request"]["succeeded"]
    result.close.assert_called_once()


def test_truncated_stream_and_fallback_are_separate_attempts(client):
    partial = stream_response({"choices": [{"delta": {"content": "partial"}}]})
    client.session.post.side_effect = [partial, response({"prompt_tokens": 8, "completion_tokens": 4})]
    with pytest.raises(IncompleteStreamError):
        list(client.chat_stream([]))
    client.chat([])
    metrics = client.metrics.snapshot()
    assert metrics["requests"] == 2
    assert metrics["failed_requests"] == 1
    assert metrics["total_duration_ms"] == 750
    assert metrics["requests_with_usage"] == 1
    partial.close.assert_called_once()


def test_cancelled_stream_is_measured_and_closed(client):
    result = stream_response({"choices": [{"delta": {"content": "partial"}}]}, "[DONE]")
    client.session.post.return_value = result
    stream = client.chat_stream([])
    assert next(stream) == "partial"
    stream.close()
    assert client.metrics.snapshot()["failed_requests"] == 1
    result.close.assert_called_once()


def test_json_failure_is_measured(client):
    result = response()
    result.json.side_effect = ValueError("invalid JSON")
    client.session.post.return_value = result
    with pytest.raises(ValueError):
        client.chat([])
    assert client.metrics.snapshot()["failed_requests"] == 1


def test_metadata_does_not_count_as_generation(client):
    client.session.post.return_value.json.return_value = {}
    client.model_metadata()
    assert client.metrics.snapshot()["requests"] == 0


def test_metrics_are_bounded_and_snapshots_cannot_mutate_counters():
    metrics = LLMMetrics()
    for i in range(100):
        metrics.record(model="test", streaming=False, succeeded=True,
                       duration_ms=1, usage={"prompt_tokens": 0, "completion_tokens": 0})
    snapshot = metrics.snapshot()
    assert snapshot["requests"] == snapshot["requests_with_usage"] == 100
    snapshot["requests"] = -1
    snapshot["last_request"]["model"] = "modified"
    assert metrics.snapshot()["requests"] == 100
    assert metrics.snapshot()["last_request"]["model"] == "test"
    assert LLMMetrics().snapshot()["requests"] == 0


def test_metrics_flow_through_service_api_and_cli(client, monkeypatch, tmp_path):
    monkeypatch.setattr(Agent, "_load_history", lambda self: None)
    agent = Agent()
    agent.llm = client
    client.session.post.return_value = response({"prompt_tokens": 9, "completion_tokens": 2})
    client.chat([])
    monkeypatch.setattr(client, "model_metadata", lambda: {})
    service = AgentService(tmp_path, agent)
    with TestClient(create_app(service, api_key="secret")) as api:
        result = api.get("/status", headers={"X-API-Key": "secret"}).json()
    assert result["runtime"]["metrics"] == client.metrics.snapshot()
    output = StringIO()
    monkeypatch.setattr(cli, "console", Console(file=output, theme=cli.THEME, width=200))
    cli.print_status(result)
    assert "last: 250 ms (ok)" in output.getvalue()
    assert "9 input / 2 output" in output.getvalue()
    assert "complete usage for 1/1 requests" in output.getvalue()
