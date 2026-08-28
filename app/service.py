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
        self.index_path = self.workspace / ".ai" / "index.db"
        self.agent = agent or Agent()

    def chat(self, message: str) -> str:
        return self.agent.run(message)

    def clear(self):
        self.agent.clear()

    def index(self):
        index_project(
            self.workspace,
            self.index_path,
        )

    def status(self) -> dict[str, int | bool]:
        if not self.index_path.exists():
            return {
                "ready": False,
                "chunks": 0,
            }

        with sqlite3.connect(self.index_path) as db:
            chunks = db.execute(
                "SELECT COUNT(*) FROM documents"
            ).fetchone()[0]

        return {
            "ready": True,
            "chunks": chunks,
        }
