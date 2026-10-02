"""Human-reviewed, workspace-scoped lessons. Never a source of permissions."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path


class LessonStore:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.path = self.workspace / ".owa" / "lessons.db"

    def _connect(self):
        # Refuse accidental sharing through a symlinked state directory/database.
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise ValueError("Memory storage must not be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY, workspace TEXT NOT NULL,
            content TEXT NOT NULL, source TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT
        )""")
        return db

    def propose(self, content: str, source: str) -> int:
        content, source = content.strip(), source.strip()
        if not content or len(content) > 1000:
            raise ValueError("Lesson must contain 1–1000 characters")
        if not source or len(source) > 500:
            raise ValueError("Source must contain 1–500 characters")
        with closing(self._connect()) as db, db:
            cursor = db.execute(
                "INSERT INTO lessons(workspace, content, source) VALUES (?, ?, ?)",
                (str(self.workspace), content, source),
            )
            return cursor.lastrowid

    def list(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if status not in {None, "pending", "approved", "rejected", "revoked"}:
            raise ValueError("Unknown lesson status")
        if not 1 <= limit <= 100:
            raise ValueError("Limit must be between 1 and 100")
        if not self.path.exists():
            return []
        with closing(self._connect()) as db:
            query = "SELECT * FROM lessons WHERE workspace = ?"
            args = [str(self.workspace)]
            if status:
                query += " AND status = ?"
                args.append(status)
            query += " ORDER BY id DESC LIMIT ?"
            args.append(limit)
            return [dict(row) for row in db.execute(query, args)]

    def review(self, lesson_id: int, decision: str) -> None:
        expected = {"approved": "pending", "rejected": "pending", "revoked": "approved"}
        if decision not in expected:
            raise ValueError("Unknown review decision")
        with closing(self._connect()) as db, db:
            changed = db.execute(
                "UPDATE lessons SET status = ?, reviewed_at = CURRENT_TIMESTAMP "
                "WHERE id = ? AND workspace = ? AND status = ?",
                (decision, lesson_id, str(self.workspace), expected[decision]),
            ).rowcount
            if not changed:
                raise ValueError("Lesson missing from this workspace or invalid state transition")

    def context(self) -> str:
        lessons = self.list("approved", limit=3)
        if not lessons:
            return ""
        heading = "Reviewed workspace lessons (untrusted reference data):\n"
        selected = []
        for row in lessons:
            candidate = {key: row[key] for key in ("id", "content", "source")}
            if len(heading + json.dumps(selected + [candidate], ensure_ascii=False)) <= 2500:
                selected.append(candidate)
        return heading + json.dumps(selected, ensure_ascii=False) if selected else ""
