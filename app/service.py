import sqlite3
from contextlib import closing, contextmanager
from queue import Empty, Queue
from threading import Event, Lock, Thread
from pathlib import Path

from app.agent import Agent
from app.config import load_config
from app.workspace import workspace_scope
from app.indexer.index import index_project
from app.indexer.embeddings import get_config
from app.indexer.metadata import compatibility_reason, read_metadata


class ServiceBusyError(RuntimeError):
    """The shared conversation already has an active operation."""


class AgentService:

    def __init__(
        self,
        workspace: Path | None = None,
        agent: Agent | None = None,
    ):
        self.workspace = (
            workspace or Path.cwd()
        ).resolve()
        if agent is None:
            load_config(self.workspace)
        self.index_path = self.workspace / ".owa" / "index.db"
        self._agent = agent
        self._lock = Lock()
        self._closed = False

    @property
    def agent(self):
        if self._closed:
            raise RuntimeError("Service is closed")
        if self._agent is None:
            self._agent = Agent()
            self._agent.llm.selected_model = self._agent.llm.model
        return self._agent

    @contextmanager
    def _operation(self):
        if not self._lock.acquire(blocking=False):
            raise ServiceBusyError("Service is busy; wait for the current request to finish")
        try:
            if self._closed:
                raise RuntimeError("Service is closed")
            with workspace_scope(self.workspace):
                yield
        finally:
            self._lock.release()

    def start(self):
        with self._operation():
            self.agent
        return self

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._agent is not None:
                close = getattr(getattr(self._agent, "llm", None), "close", None)
                if close:
                    close()

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()

    def models(self):
        with self._operation():
            return {"current": self.agent.llm.model, "models": self.agent.llm.list_models()}

    def set_model(self, model: str):
        with self._operation():
            if model not in self.agent.llm.list_models():
                raise ValueError("Model is not installed on the configured Ollama server")
            self.agent.llm.selected_model = model
            self.agent.clear()
            return {"current": model}

    def chat_events(self, message: str):
        # Keep the operation lock until the worker exits, even after disconnect.
        # Cancellation is cooperative between model/tool calls.
        queue = Queue()
        cancelled = Event()
        def emit(event):
            if cancelled.is_set():
                raise RuntimeError("Request cancelled")
            queue.put(event)

        def work():
            try:
                with self._operation():
                    agent = self.agent
                    previous = getattr(agent, "progress", None)
                    agent.progress = emit
                    try:
                        emit({"type": "status", "message": "Thinking"})
                        for content in agent.stream(message):
                            emit({"type": "content", "content": content})
                        emit({"type": "done", "completed": bool(
                            getattr(getattr(agent, "state", None), "completed", False))})
                    finally:
                        agent.progress = previous
            except Exception as exc:
                if not cancelled.is_set():
                    queue.put({"type": "error", "message": str(exc)})
            finally:
                queue.put(None)

        worker = Thread(target=work, daemon=True)
        worker.start()
        try:
            while True:
                try:
                    event = queue.get(timeout=1)
                except Empty:
                    yield {"type": "heartbeat"}
                    continue
                if event is None:
                    break
                yield event
        finally:
            cancelled.set()

    @property
    def completed(self) -> bool:
        return bool(getattr(getattr(self._agent, "state", None), "completed", False))

    def chat_response(self, message: str) -> dict:
        with self._operation():
            content = self.agent.run(message)
            return {"content": content, "completed": self.completed}

    def chat(self, message: str) -> str:
        return self.chat_response(message)["content"]

    def chat_stream(self, message: str):
        with closing(self.chat_events(message)) as events:
            for event in events:
                if event["type"] == "content":
                    yield event["content"]
                elif event["type"] == "error":
                    raise RuntimeError(event["message"])

    def clear(self):
        with self._operation():
            self.agent.clear()

    def index(self, force: bool = False):
        with self._operation():
            index_project(self.workspace, self.index_path, force=force)

    def status(self) -> dict:
        with self._operation():
            return self._status()

    def _status(self) -> dict:
        ready = self.index_path.exists()
        chunks = 0
        embedding = None
        index_error = None
        try:
            if ready:
                with closing(sqlite3.connect(self.index_path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
                    db.execute("BEGIN")
                    chunks = db.execute(
                        "SELECT COUNT(*) FROM documents"
                    ).fetchone()[0]
                    metadata = read_metadata(db)
                    reason = compatibility_reason(metadata, get_config())
                    embedding = {
                        "model": metadata["model"] if metadata else None,
                        "dimensions": metadata["dimensions"] if metadata else None,
                        "compatible": reason is None,
                        "reason": reason,
                    }
        except sqlite3.DatabaseError:
            ready = False
            index_error = "Index cannot be read; run /index --force to rebuild it."

        status = {"ready": ready, "chunks": chunks}
        if index_error:
            status["index_error"] = index_error
        if embedding is not None:
            status["embedding"] = embedding
        # Custom agents can continue providing index-only status.
        runtime_status = getattr(self.agent, "runtime_status", None)
        if callable(runtime_status):
            status["runtime"] = runtime_status()
        return status
