import sqlite3
from pathlib import Path


def connect(db_path: str | Path):
    db_path = Path(db_path)

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return sqlite3.connect(db_path)


def initialize(db_path: str | Path):
    with connect(db_path) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                file_hash TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(path, chunk_index)
            )
            """
        )

        db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_path
            ON documents(path)
            """
        )

        db.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                path,
                content,
                content='documents',
                content_rowid='id'
            )
            """
        )

        db.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS documents_fts_insert
            AFTER INSERT ON documents
            BEGIN
                INSERT INTO documents_fts(rowid, path, content)
                VALUES (new.id, new.path, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_fts_delete
            AFTER DELETE ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, path, content)
                VALUES ('delete', old.id, old.path, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS documents_fts_update
            AFTER UPDATE OF path, content ON documents
            BEGIN
                INSERT INTO documents_fts(documents_fts, rowid, path, content)
                VALUES ('delete', old.id, old.path, old.content);
                INSERT INTO documents_fts(rowid, path, content)
                VALUES (new.id, new.path, new.content);
            END;
            """
        )

        db.execute("INSERT INTO documents_fts(documents_fts) VALUES ('rebuild')")

        try:
            db.execute("ALTER TABLE documents ADD COLUMN file_hash TEXT")
        except Exception:
            pass

        db.commit()
