"""Check incremental HTTP progress with a blocked model stub; no Ollama required."""
import json
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
from threading import Event, Thread
from types import SimpleNamespace
import time

import requests
import uvicorn

from app.api import create_app
from app.service import AgentService

release = Event()
class Agent:
    state = SimpleNamespace(completed=False)
    def stream(self, message):
        self.progress({'type': 'tool_start', 'tool': 'read_file'})
        if not release.wait(5):
            raise RuntimeError('Progress did not reach the HTTP client')
        self.progress({'type': 'tool_end', 'tool': 'read_file', 'succeeded': True})
        yield 'verified café response'
        self.state.completed = True

with TemporaryDirectory(prefix='owa-http-eval-') as directory:
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    port = listener.getsockname()[1]
    service = AgentService(Path(directory), Agent())
    server = uvicorn.Server(uvicorn.Config(create_app(service), log_level='error'))
    thread = Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(.02)
        from app.api_client import ApiClient
        client = ApiClient(f'http://127.0.0.1:{port}')
        client.session.trust_env = False
        events = client.chat_events('read')
        first = next(events)
        assert first['type'] == 'status'
        second = next(events)
        assert second == {'type': 'tool_start', 'tool': 'read_file'}
        # The model stub is still blocked: these events arrived incrementally.
        release.set()
        rest = list(events)
        assert rest[-1] == {'type': 'done', 'completed': True}
        assert any(event.get('content') == 'verified café response' for event in rest)
        client.close()
        print(json.dumps({'passed': True, 'progress_before_model_completion': True,
                          'unicode_preserved': True, 'events': [first, second] + rest}))
    finally:
        release.set()
        server.should_exit = True
        thread.join(5)
        listener.close()
        assert not thread.is_alive()
