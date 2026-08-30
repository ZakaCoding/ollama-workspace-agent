# OwA — Ollama Workspace Agent

[![PyPI](https://img.shields.io/pypi/v/ollama-workspace-agent.svg)](https://pypi.org/project/ollama-workspace-agent/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/github/stars/ZakaCoding/ollama-workspace-agent?style=social)](https://github.com/ZakaCoding/ollama-workspace-agent)

**A local, privacy‑first coding agent that understands your codebase and edits files on your machine.**  
Runs entirely on your own hardware via Ollama — no cloud, no telemetry, no external API keys.

- Chat with your project using a local LLM
- Semantic search across your codebase
- Safe, review‑before‑run shell commands
- Git‑aware workflow (status, diff, log)
- Optional HTTP API for integration with other tools

---

## Quick Start

1. **Install Ollama and models**

   ```bash
   # Install Ollama: https://ollama.com
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text
   ```

2. **Install OwA**

   ```bash
   pip install ollama-workspace-agent
   # or, for an isolated install:
   pipx install ollama-workspace-agent
   ```

3. **Run in your project**

   ```bash
   cd your-project
   owa
   ```

4. **Configure once**

   On first run, type `/setup` and follow the prompts.  
   Config is saved to `~/.config/owa/.env`.

5. **Start coding**

   Try prompts like:
   - “Where is the auth logic implemented?”
   - “Add input validation to `app/api.py` and show me the diff.”
   - “Run the tests and summarize failures.”

---

## Requirements

- Python 3.11+
- Ollama running on a reachable machine
- A chat model installed on Ollama, e.g. `llama3.1:8b`
- An embedding model installed on Ollama, e.g. `nomic-embed-text`

---

## Configuration

Run `/setup` inside OwA, or manually create `~/.config/owa/.env`:

```env
# ~/.config/owa/.env

# Ollama on the same machine
LLM_BASE_URL=http://127.0.0.1:11434/v1
EMBEDDING_BASE_URL=http://127.0.0.1:11434

# Or Ollama on another machine in your LAN
# LLM_BASE_URL=http://192.168.1.50:11434/v1
# EMBEDDING_BASE_URL=http://192.168.1.50:11434

LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text

# Optional: protect the HTTP API
API_KEY=choose-a-private-api-key
```

You can also place a `.env` in your project root to override the global config for that project.

- `LLM_BASE_URL` uses Ollama’s OpenAI‑compatible `/v1` API.
- `EMBEDDING_BASE_URL` uses Ollama’s native `/api/embed` API.
- If Ollama runs on the same machine, use `127.0.0.1` as the host.

### Troubleshooting config

- Verify Ollama is running:

  ```bash
  curl http://127.0.0.1:11434/api/tags
  ```

  A successful response contains a `models` list.

- Ensure the models in your config are installed:

  ```bash
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
  ```

- For remote Ollama, make sure the host’s firewall allows port `11434`.

---

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

---

## Indexing

OwA auto‑indexes your project on first run. Common directories are excluded automatically (`node_modules`, `dist`, `build`, `.github`, `.git`, `.venv`, etc.).

To exclude additional files or directories, create a `.owaignore` in your project root:

```text
# .owaignore
secrets.json
fixtures/
*.min.js
```

The local index is stored in `.owa/` and is automatically added to your `.gitignore` on first index.

---

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

Example prompts:

- “Search for where we handle JWT expiration and suggest improvements.”
- “Patch `app/api.py` to add request validation using Pydantic.”
- “Run `pytest -q` and summarize failing tests.”
- “Show me the current git diff and explain what changed.”

---

## API Mode

Run the HTTP API:

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

Use the CLI as an API client:

```bash
owa --api-url http://127.0.0.1:8000
```

Or call directly with `curl`:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "Explain the main entry point in this project"}'
```

Available endpoints: `GET /health`, `GET /status`, `POST /chat`, `POST /chat/stream`, `POST /clear`, `POST /index`.

When `API_KEY` is configured, include it in the `X-API-Key` header for every endpoint except `/health`.

---

## Privacy & Safety

- All inference and embeddings run on your own Ollama server.
- No code or conversation leaves your machine unless you explicitly call a remote API.
- Shell commands require explicit user confirmation before execution.
- Sensitive paths and common noise directories are excluded from indexing by default.
- The project index lives in `.owa/` and is automatically added to `.gitignore`.

---

## Why OwA?

OwA is designed for developers who want:

- **Fully local inference**: No cloud dependencies; just Ollama + your models.
- **Codebase awareness**: Automatic indexing and semantic search over your repo.
- **Safe editing**: Patch/write files and run commands only after your approval.
- **Simple deployment**: Single Python package, minimal config, works on laptop or server.

Compared to heavier frameworks, OwA aims to be:

- Easy to install and run (`pip install` + `owa`)
- Transparent and hackable (clear project layout, simple agent loop)
- Focused on day‑to‑day coding tasks rather than complex orchestration

---

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

---

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

---

## Contributing

Contributions are welcome! Feel free to:

- Open issues for bugs, ideas, or questions
- Submit pull requests for improvements or new tools
- Share workflows or prompts that work well with OwA

---

## License

Licensed under the MIT License. See [LICENSE](LICENSE) for details.