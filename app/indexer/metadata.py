"""Embedding provenance and compatibility checks for the local index."""

import hashlib
import math
import sqlite3


FORMAT_VERSION = 1


def embedding_identity(config: tuple[str, str]) -> dict:
    endpoint, model = config
    return {
        "format_version": FORMAT_VERSION,
        "model": model,
        # URLs may contain credentials; store only a fingerprint.
        "endpoint_hash": hashlib.sha256(endpoint.encode()).hexdigest(),
    }


def read_metadata(db: sqlite3.Connection) -> dict | None:
    if not db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'index_metadata'"
    ).fetchone():
        return None
    row = db.execute(
        "SELECT format_version, model, endpoint_hash, dimensions FROM index_metadata WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return dict(zip(("format_version", "model", "endpoint_hash", "dimensions"), row))


def write_metadata(db: sqlite3.Connection, config: tuple[str, str], dimensions: int | None = None):
    identity = embedding_identity(config)
    db.execute(
        "INSERT INTO index_metadata (id, format_version, model, endpoint_hash, dimensions) VALUES (1, ?, ?, ?, ?)",
        (identity["format_version"], identity["model"], identity["endpoint_hash"], dimensions),
    )


def compatibility_reason(metadata: dict | None, config: tuple[str, str]) -> str | None:
    if metadata is None:
        return "embedding metadata is missing"
    expected = embedding_identity(config)
    if metadata["format_version"] != expected["format_version"]:
        return "index format has changed"
    if metadata["model"] != expected["model"]:
        return "embedding model has changed"
    if metadata["endpoint_hash"] != expected["endpoint_hash"]:
        return "embedding endpoint has changed"
    dimensions = metadata["dimensions"]
    if dimensions is not None and (type(dimensions) is not int or dimensions <= 0):
        return "embedding dimensions are invalid"
    return None


def vector_dimensions(vector) -> int:
    if not isinstance(vector, list) or not vector:
        raise ValueError("Embedding must be a non-empty vector")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
        raise ValueError("Embedding values must be finite numbers")
    return len(vector)
