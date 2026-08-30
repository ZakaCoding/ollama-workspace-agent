import os

import httpx


EMBEDDING_BASE_URL = os.getenv(
    "EMBEDDING_BASE_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "nomic-embed-text",
)


def embed(text: str) -> list[float]:

    response = httpx.post(
        f"{EMBEDDING_BASE_URL}/api/embed",
        json={
            "model": EMBEDDING_MODEL,
            "input": text,
        },
        timeout=300,
    )

    response.raise_for_status()

    data = response.json()

    embeddings = data.get("embeddings")

    if not embeddings:
        raise RuntimeError(
            "Ollama returned no embedding."
        )

    return embeddings[0]
