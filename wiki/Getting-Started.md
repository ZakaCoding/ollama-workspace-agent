# Getting Started

## Requirements

- Python 3.11 or newer
- Ollama reachable from the agent machine
- A chat model installed in Ollama, such as `ornith:9b`
- An embedding model installed in Ollama, such as `nomic-embed-text`

## Install

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv requests httpx pytest
```

The existing runtime uses `requests` for chat calls and `httpx` for embeddings.

## Configure

Create a private `.env` file in the repository root:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=ornith:9b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
```

`.env` is ignored by Git. Do not place credentials or private host details in source files or wiki pages.

Check that Ollama is reachable:

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

## Run the agent

```bash
source .venv/bin/activate
python main.py
```

Enter a request at the `You` prompt. Use `exit`, `quit`, `/exit`, or `/quit` to stop.

## Build the code index

The indexer currently exposes a Python API rather than a CLI command:

```python
from pathlib import Path
from app.indexer.index import index_project

index_project(Path.cwd(), Path(".ai/index.db"))
```

The operation calls Ollama's `/api/embed` endpoint and writes the SQLite index to `.ai/index.db`. The `.ai/` directory is ignored by Git.

Once an index exists, the agent can use the registered `search_code` tool. It searches by embedding similarity and falls back to keyword overlap when the embedding request fails with an HTTP error.

## Verify the installation

```bash
PYTHONPATH=. pytest -q
python -m compileall -q main.py app tests
```

The test suite covers workspace path rejection, task-state isolation, shell confirmation behavior, and calculator operations.

## Common setup problems

- **`ModuleNotFoundError: app`**: run commands from the repository root or set `PYTHONPATH=.`.
- **Embedding connection failure**: verify `EMBEDDING_BASE_URL`, Ollama availability, and the installed embedding model.
- **No search results**: build the index first and confirm that the requested file extensions are supported.
- **Unsafe command rejected**: commands are intentionally bounded to the configured workspace.
