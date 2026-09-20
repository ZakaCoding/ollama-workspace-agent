import sqlite3
from contextlib import closing
from pathlib import Path

from app.agent import Agent
from app.indexer.index import index_project
from app.indexer.embeddings import get_config
from app.indexer.metadata import compatibility_reason, read_metadata


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

    def index(self, force: bool = False):
        index_project(
            self.workspace,
            self.index_path,
            force=force,
        )

    def status(self) -> dict:
        ready = self.index_path.exists()
        chunks = 0
        embedding = None
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

        status = {"ready": ready, "chunks": chunks}
        if embedding is not None:
            status["embedding"] = embedding
        # Custom agents can continue providing index-only status.
        runtime_status = getattr(self.agent, "runtime_status", None)
        if callable(runtime_status):
            status["runtime"] = runtime_status()
        return status
