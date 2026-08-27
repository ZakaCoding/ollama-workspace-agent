import json
import sqlite3


def save_chunk(
    db: sqlite3.Connection,
    path: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
):
    db.execute(
        """
        INSERT INTO documents (
            path,
            chunk_index,
            content,
            embedding
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(path, chunk_index)
        DO UPDATE SET
            content = excluded.content,
            embedding = excluded.embedding,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            path,
            chunk_index,
            content,
            json.dumps(embedding),
        ),
    )

    db.commit()
