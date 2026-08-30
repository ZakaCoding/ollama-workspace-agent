Licensed under the MIT License. See [LICENSE](LICENSE) for details.

# OwA — Ollama Workspace Agent

An open-source local coding assistant powered by Ollama. Runs entirely on your own hardware — no cloud, no telemetry, no API keys required beyond your own Ollama server.

## Install

```bash
pip install ollama-workspace-agent
```

Or with pipx for an isolated install:

```bash
pipx install ollama-workspace-agent
```

## Requirements

- Python 3.11+
- Ollama running on a reachable machine
- A chat model installed on Ollama, such as `llama3.1:8b`
- An embedding model installed on Ollama, such as `nomic-embed-text`

## Quick Start

```bash
cd your-project
owa
```

On first run, type `/setup` to configure your Ollama connection. OwA will walk you through it interactively and save the config to `~/.config/owa/.env`.

Then just start chatting — OwA will auto-index your project on startup.

## Configuration

Run `/setup` inside OwA, or manually create `~/.config/owa/.env`:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=llama3.1:8b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
API_KEY=choose-a-private-api-key
```

You can also place a `.env` in your project root to override the global config for that project.

`LLM_BASE_URL` uses Ollama's OpenAI-compatible `/v1` API. `EMBEDDING_BASE_URL` uses Ollama's native `/api/embed` API. If Ollama runs on the same machine, replace `YOUR_OLLAMA_HOST` with `127.0.0.1`.

## Verify Ollama

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

A successful response contains a `models` list. Make sure the models in your config are installed:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## CLI Commands

| Command   | Description                        |
|-----------|------------------------------------|
| `/setup`  | Configure Ollama connection        |
| `/model`  | Switch the active chat model       |
| `/index`  | Rebuild the project index          |
| `/status` | Show index status                  |
| `/clear`  | Clear conversation history         |
| `/help`   | Show available commands            |
| `/quit`   | Exit                               |

## Indexing

OwA auto-indexes your project on first run. Common directories are excluded automatically (`node_modules`, `dist`, `build`, `.github`, `.git`, `.venv`, etc.).

To exclude additional files or directories, create a `.owaignore` in your project root:

```
# .owaignore
secrets.json
fixtures/
*.min.js
```

The local index is stored in `.owa/` and is automatically added to your `.gitignore` on first index.

## API Mode

Run the HTTP API:

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Use the CLI as an API client:

```bash
owa --api-url http://127.0.0.1:8000
```

Available endpoints: `GET /health`, `GET /status`, `POST /chat`, `POST /chat/stream`, `POST /clear`, `POST /index`.

When `API_KEY` is configured, include it in the `X-API-Key` header for every endpoint except `/health`.

## Tools

The agent can call these workspace tools:

| Tool          | Description                                          |
|---------------|------------------------------------------------------|
| `list_dir`    | List files and directories                           |
| `read_file`   | Read UTF-8 text files                                |
| `patch_file`  | Targeted search-and-replace edit on an existing file |
| `write_file`  | Create or fully replace a file                       |
| `search_code` | Semantic search over the indexed codebase            |
| `code_review` | Review Python files for common security risks        |
| `run_command` | Run a shell command after user confirmation          |
| `git_status`  | Show Git branch and working tree status              |
| `git_diff`    | Show current Git diff                                |
| `git_log`     | Show recent Git commits                              |

## Project Layout

```text
.
├── app/
│   ├── agent/       Agent orchestration and system prompt
│   ├── api.py       FastAPI endpoints and request models
│   ├── cli.py       CLI entry point
│   ├── config.py    Global config path resolution
│   ├── service.py   Shared chat, indexing, and status service
│   ├── indexer/     Code indexing and semantic search
│   ├── llm/         OpenAI-compatible Ollama client
│   └── tools/       Workspace tool implementations and registry
├── demo/            Small demo code
├── main.py          Thin shim for `python main.py`
├── CHANGELOG.md     Project change history
└── README.md        Project documentation
```

## Development

Clone and install in editable mode:

```bash
git clone https://github.com/ZakaCoding/ollama-workspace-agent
cd ollama-workspace-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest tests/ -v
```

Compile check:

```bash
python -m py_compile main.py app/agent/*.py app/indexer/*.py app/llm/*.py app/tools/*.py
```
