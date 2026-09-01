# Indexing and Search

The indexer gives the agent a local semantic view of source code. It is separate from the chat model and stored in a SQLite database under `.owa/`.

## Auto-indexing

OwA auto-indexes your project on first run. The index is stored in `.owa/index.db` and `.owa/` is automatically added to your `.gitignore`.

To rebuild the index manually, run `/index` inside OwA.

## Excluded directories

The following directories are always excluded from indexing:

`.git`, `.venv`, `venv`, `env`, `node_modules`, `__pycache__`, `.idea`, `.vscode`, `.owa`, `.github`, `.gitlab`, `dist`, `build`, `out`, `coverage`, `.next`, `.nuxt`, `.cache`, `vendor`, `target`, `bin`, `obj`

## Custom exclusions with .owaignore

Create a `.owaignore` file in your project root to exclude additional files or directories:

```
# .owaignore
secrets.json
fixtures/
*.min.js
logs/
```

Same syntax as `.gitignore` — one pattern per line, `#` for comments.

## Supported file types

Python, JavaScript, TypeScript, JSX, TSX, PHP, Go, Rust, Java, C, C++, CSS, SCSS, HTML, JSON, YAML, TOML, Markdown, text, SQL, shell scripts, and Blade templates.

## Chunking

`chunk_text` defaults to a 12,000-character chunk size with 1,000 characters of overlap. Empty input returns no chunks.

## Query behavior

`search_code(query, limit=5)` reads `.owa/index.db` and returns formatted results containing the file path, chunk index, similarity score, and content.

Ranking:

1. The query is embedded through Ollama's `/api/embed`.
2. Each stored vector receives a cosine similarity score.
3. Results are sorted descending and limited.
4. If the embedding request fails with an HTTP error, keyword overlap is used as a fallback.

## Operational notes

- The indexer requires Ollama's embedding service to be running during indexing.
- Vectors are loaded and scored in Python — may be slow for very large repositories.
- The database has no vector index.
- Rebuild the index after changing your embedding model — stored vectors will be incompatible.
- The indexer does not remove records for deleted files — a full `/index` rebuild clears stale entries.
