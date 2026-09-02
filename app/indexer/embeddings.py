import os

import httpx


def _get_config() -> tuple[str, str]:
    base_url = os.getenv("EMBEDDING_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    return base_url, model


def embed(text: str) -> list[float]:
    base_url, model = _get_config()

    response = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": text},
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    embeddings = data.get("embeddings")

    if not embeddings:
        raise RuntimeError("Ollama returned no embedding.")

    return embeddings[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single Ollama request."""
    if not texts:
        return []

    base_url, model = _get_config()

    response = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": texts},
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    embeddings = data.get("embeddings")

    if not embeddings:
        raise RuntimeError("Ollama returned no embeddings.")

    return embeddings
