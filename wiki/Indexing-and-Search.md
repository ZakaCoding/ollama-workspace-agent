# Indexing and Search

OwA uses a local semantic index so the agent can find relevant project context before opening many files. The index is intentionally simple and local-first: it does not depend on a remote search backend.

## Supported files

The indexer reads common code and config files such as:

- Python, JavaScript, TypeScript, and Go
- Rust, Java, C/C++, and shell scripts
- HTML, CSS, JSON, YAML, TOML, SQL, and Markdown
- many text-based project files used in developer workflows

It ignores generated or dependency-heavy folders such as `.git`, `.venv`, `node_modules`, `dist`, `build`, and local caches.

## Local storage

The index is stored under `.owa/` and is tied to the repository. Each indexed chunk keeps:

- the relative file path
- the chunk position
- the original source text
- the serialized embedding
- creation and update metadata

This allows the agent to search semantically for likely relevant files without blindly opening everything.

## Index flow

```python
from pathlib import Path
from app.indexer.index import index_project

index_project(
    workspace=Path.cwd(),
    db_path=Path(".owa/index.db"),
)
```

The process is:

1. walk the project and filter files
2. split files into overlapping chunks
3. embed each chunk with Ollama
4. store path, content, and embedding in SQLite
5. rank query results by similarity when the user asks for project-specific search

## Query behavior

The `search_code` tool embeds the query, compares it against stored chunk embeddings, and returns the most relevant segments. If the embedding service fails, it falls back to a simple keyword-based comparison so the agent still has some retrieval signal.

This is a pragmatic design: it is easy to inspect, easy to debug, and well aligned with the local-first personality of the project.

## Current limits

The indexing system is intentionally lightweight and does not yet include advanced features such as:

- vector database tuning
- stale chunk cleanup
- repository-level hybrid ranking
- automatic index migration tooling

These are natural follow-ups for a public open-source project that wants better retrieval quality without heavy infrastructure.

## Research directions

Good future experiments include:

- comparing chunk sizes and overlap settings
- measuring retrieval quality on benchmark prompts
- adding stale-record cleanup for removed files
- trying hybrid semantic + keyword ranking
- optimizing for larger repos and noisy generated output
