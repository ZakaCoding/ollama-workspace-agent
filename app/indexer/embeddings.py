import os

import httpx


def embed(text: str) -> list[float]:
    base_url = os.getenv("EMBEDDING_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")

    response = httpx.post(
        f"{base_url}/api/embed",
        json={
            "model": model,
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
