import sqlite3
from pathlib import Path

from app.agent import Agent
from app.indexer.index import index_project


class AgentService:

    def __init__(
        self,
        workspace: Path | None = None,
        agent: Agent | None = None,
    ):
        self.workspace = (
            workspace or Path.cwd()
        ).resolve()
        self.index_path = self.workspace / ".owa" / "index.db"
        self.agent = agent or Agent()

    def chat(self, message: str) -> str:
        return self.agent.run(message)

    def chat_stream(self, message: str):
        return self.agent.stream(message)

    def clear(self):
        self.agent.clear()

    def index(self):
        index_project(
            self.workspace,
            self.index_path,
        )

    def status(self) -> dict:
        ready = self.index_path.exists()
        chunks = 0
        if ready:
            with sqlite3.connect(self.index_path) as db:
                chunks = db.execute(
                    "SELECT COUNT(*) FROM documents"
                ).fetchone()[0]

        status = {"ready": ready, "chunks": chunks}
        # Custom agents can continue providing index-only status.
        runtime_status = getattr(self.agent, "runtime_status", None)
        if callable(runtime_status):
            status["runtime"] = runtime_status()
        return status
