from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.service import AgentService


class StreamingAgent:
    def __init__(self):
        self.llm = Mock()
        self.llm.model = 'old'
        self.llm.list_models.return_value = ['old', 'new']
        self.state = SimpleNamespace(completed=False)
        self.clear = Mock()

    def stream(self, message):
        self.progress({'type': 'tool_start', 'tool': 'read_file'})
        self.progress({'type': 'tool_end', 'tool': 'read_file', 'succeeded': True})
        yield 'verified response'
        self.state.completed = True


def test_service_start_is_lazy_and_close_is_idempotent(tmp_path, monkeypatch):
    agent = StreamingAgent()
    factory = Mock(return_value=agent)
    monkeypatch.setattr('app.service.Agent', factory)
    service = AgentService(tmp_path)
    factory.assert_not_called()
    with service:
        service.start()
        factory.assert_called_once()
    service.close()
    agent.llm.close.assert_called_once()
    with pytest.raises(RuntimeError, match='closed'):
        service.clear()


def test_events_preserve_tool_order_and_verified_content(tmp_path):
    agent = StreamingAgent()
    service = AgentService(tmp_path, agent)
    events = list(service.chat_events('read'))
    assert [event['type'] for event in events] == ['status', 'tool_start', 'tool_end', 'content', 'done']
    assert events[-1]['completed'] is True
    assert agent.progress is None
    assert ''.join(service.chat_stream('read')) == 'verified response'


def test_failure_becomes_error_event_and_service_remains_usable(tmp_path):
    agent = StreamingAgent()
    agent.stream = Mock(side_effect=ValueError('model unavailable'))
    service = AgentService(tmp_path, agent)
    events = list(service.chat_events('read'))
    assert events[-1] == {'type': 'error', 'message': 'model unavailable'}
    assert not any(event['type'] == 'done' for event in events)
    service.clear()
    assert agent.progress is None


def test_disconnect_keeps_busy_until_worker_stops(tmp_path):
    entered, release, stopped = Event(), Event(), Event()
    agent = StreamingAgent()
    def slow(message):
        entered.set()
        try:
            assert release.wait(5)
            agent.progress({'type': 'tool_start', 'tool': 'read_file'})
            yield 'should not appear'
        finally:
            stopped.set()
    agent.stream = slow
    service = AgentService(tmp_path, agent)
    events = service.chat_events('slow')
    assert next(events)['type'] == 'status'
    assert entered.wait(2)
    try:
        assert next(events)['type'] == 'heartbeat'
        with pytest.raises(RuntimeError, match='busy'):
            service.clear()
        events.close()
        with pytest.raises(RuntimeError, match='busy'):
            service.set_model('new')
    finally:
        release.set()
    assert stopped.wait(2)
    service.close()
    assert agent.progress is None


def test_model_switch_validates_and_clears_only_on_success(tmp_path):
    agent = StreamingAgent()
    service = AgentService(tmp_path, agent)
    with pytest.raises(ValueError, match='not installed'):
        service.set_model('absent')
    agent.clear.assert_not_called()
    assert service.models() == {'current': 'old', 'models': ['old', 'new']}
    assert service.set_model('new') == {'current': 'new'}
    assert agent.llm.selected_model == 'new'
    agent.clear.assert_called_once()


def test_api_lifecycle_and_authenticated_events(tmp_path):
    agent = StreamingAgent()
    service = AgentService(tmp_path, agent)
    with TestClient(create_app(service, api_key='key')) as client:
        assert client.post('/chat/events', json={'message': 'read'}).status_code == 401
        response = client.post('/chat/events', json={'message': 'read'}, headers={'X-API-Key': 'key'})
        import json
        events = [json.loads(line) for line in response.text.splitlines()]
        assert events[-1] == {'type': 'done', 'completed': True}
        assert response.headers['content-type'].startswith('application/x-ndjson')
        assert client.post('/model', json={'model': 'absent'}, headers={'X-API-Key': 'key'}).status_code == 400
    agent.llm.close.assert_called_once()


def test_corrupt_index_has_actionable_diagnostic(tmp_path):
    service = AgentService(tmp_path, StreamingAgent())
    service.index_path.parent.mkdir()
    service.index_path.write_text('not sqlite')
    status = service.status()
    assert not status['ready']
    assert '/index --force' in status['index_error']


def test_services_bind_tools_and_history_to_their_own_workspaces(tmp_path):
    from app.tools.filesystem import read_file
    from app.workspace import current_workspace
    class WorkspaceAgent(StreamingAgent):
        def stream(self, message):
            yield read_file('marker.txt')
            self.state.completed = True
    first, second = tmp_path / 'first', tmp_path / 'second'
    first.mkdir()
    second.mkdir()
    (first / 'marker.txt').write_text('first workspace')
    (second / 'marker.txt').write_text('second workspace')
    original = current_workspace()
    with AgentService(first, WorkspaceAgent()) as a, AgentService(second, WorkspaceAgent()) as b:
        assert ''.join(a.chat_stream('read')) == 'first workspace'
        assert ''.join(b.chat_stream('read')) == 'second workspace'
    assert current_workspace() == original


def test_real_agent_history_is_scoped_to_service_workspace(tmp_path):
    service = AgentService(tmp_path)
    with service:
        service.agent.messages.append({'role': 'user', 'content': 'local history'})
        with service._operation():
            service.agent._save_history()
        assert (tmp_path / '.owa/history.json').exists()
        assert str(tmp_path) in service.agent.messages[0]['content']
        service.clear()
        assert not (tmp_path / '.owa/history.json').exists()


def test_api_reports_busy_and_incomplete_tasks(tmp_path):
    agent = StreamingAgent()
    agent.run = lambda message: 'stopped before verification'
    service = AgentService(tmp_path, agent)
    with TestClient(create_app(service)) as client:
        with service._operation():
            assert client.get('/status').status_code == 409
            assert client.post('/clear').status_code == 409
        response = client.post('/chat', json={'message': 'change'})
        assert response.json() == {'content': 'stopped before verification', 'completed': False}
