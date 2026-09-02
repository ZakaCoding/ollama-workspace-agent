import json
import sqlite3


def save_chunk(
    db: sqlite3.Connection,
    path: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    file_hash: str = "",
):
    db.execute(
        """
        INSERT INTO documents (
            path,
            chunk_index,
            content,
            embedding,
            file_hash
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(path, chunk_index)
        DO UPDATE SET
            content = excluded.content,
            embedding = excluded.embedding,
            file_hash = excluded.file_hash,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            path,
            chunk_index,
            content,
            json.dumps(embedding),
            file_hash,
        ),
    )

    db.commit()
