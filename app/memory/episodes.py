"""Small, local record of completed workspace changes.

This stores task metadata rather than model responses or file contents. The
records are treated as untrusted context when shown to the model.
"""

import json
import sqlite3
from pathlib import Path


class EpisodeStore:
    def __init__(self, workspace: Path):
        self.path = workspace / ".owa" / "episodes.db"

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.execute("""CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY, task TEXT NOT NULL, files TEXT NOT NULL,
            verified INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        return db

    def record(self, task: str, files: list[str], verified: bool):
        if not files:
            return
        with self._connect() as db:
            db.execute(
                "INSERT INTO episodes(task, files, verified) VALUES (?, ?, ?)",
                (task[:500], json.dumps(files[:30]), int(verified)),
            )

    def recent(self, limit: int = 3) -> list[dict]:
        if not self.path.exists():
            return []
        with self._connect() as db:
            rows = db.execute(
                "SELECT task, files, verified, created_at FROM episodes ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(task=task, files=json.loads(files), verified=bool(verified),
                     created_at=created_at) for task, files, verified, created_at in rows]
