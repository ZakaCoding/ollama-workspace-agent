# Indexing and Search

The indexer gives the agent a local semantic view of source code. It is separate from the chat model and is stored in a SQLite database under `.ai/`.

## Supported files

The indexer currently considers common source and text extensions, including Python, JavaScript, TypeScript, PHP, Go, Rust, Java, C/C++, CSS, HTML, JSON, YAML, TOML, Markdown, text, SQL, and shell scripts.

It ignores common generated or dependency directories such as `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.idea`, `.vscode`, and `.ai`.

## Indexing API

```python
from pathlib import Path
from app.indexer.index import index_project

index_project(
    workspace=Path.cwd(),
    db_path=Path(".ai/index.db"),
)
```

Each indexed chunk stores:

- relative file path
- chunk index
- source content
- serialized embedding
- creation and update timestamps

Existing `(path, chunk_index)` records are updated when re-indexed. The current indexer does not remove records for files or chunks that no longer exist, so a full cleanup strategy is an important future improvement.

## Chunking

`chunk_text` defaults to a 12,000-character chunk size with 1,000 characters of overlap. Empty input returns no chunks. An overlap equal to or larger than the chunk size raises `ValueError`.

## Query behavior

`search_code(query, limit=5)` reads `.ai/index.db` and returns formatted results containing the file, chunk, similarity score, and content.

Ranking behavior:

1. The query is embedded through Ollama.
2. Each stored vector receives cosine similarity.
3. Results are sorted descending and limited.
4. If the embedding request raises an HTTP error, keyword overlap is used as a fallback.

The fallback is intentionally modest: it compares normalized alphanumeric and underscore terms. It is not a replacement for semantic retrieval.

## Operational limits

- The indexer requires an embedding service during indexing.
- Vectors are loaded and scored in Python, which may be slow for large indexes.
- The database has no vector index.
- Search currently catches HTTP errors, but network and configuration failures should be handled more comprehensively.
- The database is local state and should be rebuilt when its schema or embedding model changes.

## Research opportunities

Useful experiments include comparing chunk sizes, measuring overlap waste, testing hybrid keyword and vector ranking, adding stale-record deletion, and evaluating retrieval quality on a fixed set of developer questions.
