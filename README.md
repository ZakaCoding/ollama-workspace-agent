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

# Optional small-model resource controls
OWA_CONTEXT_TOKENS=8192
OWA_MAX_OUTPUT_TOKENS=1024
```

You can also place a `.env` in your project root to override the global config for that project.

`OWA_CONTEXT_TOKENS` controls the repository evidence budget. `OWA_MAX_OUTPUT_TOKENS` limits each model response. Both settings are bounded by OwA and can be lowered for small models or low-resource machines.

Large retrieved chunks are compressed into query-focused source excerpts without
an extra model call. Omitted text is marked explicitly, original chunk citations
are retained, and the character budget includes evidence headers and separators.
The budget is shared across eligible results; duplicate chunks from the same file
are skipped. Excerpts may omit relevant details, so inspect the full file when
more context is needed.


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

Ask `learn this project` for a cited overview of selected current files, without
building an index or requesting embeddings. The overview respects `.owaignore`,
skips dependency directories and symlinks, and stays within the context budget.
It reads excerpts from at most six files; it does not train the model or retain
permanent project knowledge.

Direct requests such as `List files`, `Show calculator.py`, or
`Run python --version` use the corresponding tools. Explicit fixes can combine
Git inspection, edits, and test execution in one request. OwA checks that a
requested command actually ran before accepting a completion response.

For a live small-model agent check, run
`python scripts/eval-agent.py --model qwen2.5-coder:7b --output .owa/eval.json`.
It uses your configured Ollama connection and disposable projects. See
[Agent evaluation](wiki/Agent-Evaluation.md) for checks and limitations.

| Command   | Description                        |
|-----------|------------------------------------|
| `/setup`  | Configure Ollama connection        |
| `/model`  | Switch the active chat model       |
| `/index`  | Update changed files in the project index |
| `/index --force` | Rebuild all indexed embeddings |
| `/status` | Show index, budgets, and model capabilities |
| `/clear`  | Clear conversation history         |
| `/help`   | Show available commands            |
| `/quit`   | Exit                               |

The index records its embedding model, endpoint fingerprint, and vector
dimensions in `.owa/index.db`. Changing the embedding model or endpoint causes
the next `/index` to rebuild all vectors. Until then, incompatible or legacy
indexes use lexical search. `/status` reports embedding compatibility.
Use `/index --force` after replacing a model under the same name or to repair
invalid vectors. Failed updates preserve the previous index; successful updates
remove deleted, excluded, and obsolete chunks. API clients can request a full
rebuild with `POST /index?force=true`.

Startup and `/status` show the active model, OwA context budget, evidence
character cap, and output token limit. Model capabilities and maximum context
are read from Ollama when available; unavailable metadata displays as `unknown`.
The model maximum is metadata, not the context size currently allocated by
Ollama. OwA's context budget controls retrieval and does not configure Ollama's
context allocation. Metadata requests use a short two-second timeout and do
not generate a response. In API mode, diagnostics come from the server.

After model requests, `/status` also shows request counts, failures/interrupted
streams, last and total elapsed time, and reported input/output token totals.
Usage coverage shows how many requests supplied both token counts; missing
usage is not estimated. Each planning, retry, and fallback request counts
separately. These measurements live only in memory for the lifetime of the
agent client; `/clear` clears conversation history but does not reset them.
Metrics store no prompts or response text and send no telemetry. Request
latency includes transport and model time (and consumer time for streaming),
not the entire user task. Embedding and metadata requests are excluded.

---

## Indexing

Run `/index` when you want to build the project index. CLI and API startup do not automatically index or load a model. Common directories are excluded automatically (`node_modules`, `dist`, `build`, `.github`, `.git`, `.venv`, etc.).

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

For automatic Tailscale startup and remote Ollama access in GitHub Codespaces,
see [Codespaces setup](wiki/Codespaces.md).

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


## Service lifecycle and progress

Direct CLI and HTTP API use the same service startup, workspace binding, model
selection, and cleanup. Indexing is explicit in both modes. One service handles
one active operation at a time; a second mutation is rejected while a request is
running. Separate services bind file tools, commands, search, and history to
their own workspaces without changing the process directory.

`/model` lists installed models from the active service and switches immediately.
The selection lasts for that service session and clears its conversation. In API
mode it changes the server session; `/setup` still configures the local machine
for its next startup. `GET /models` and `POST /model` with `{"model":"name"}` expose
this behavior to API clients. These endpoints use the configured API key.

`POST /chat/events` accepts `{"message":"your request"}` and streams newline-delimited
JSON. Events are `status`, `tool_start`, `tool_end`, `heartbeat`, `content`, `done`,
or `error`. Heartbeats arrive approximately once a second while waiting. A `done`
event includes the agent's `completed` flag; an error or a missing final event is
not successful completion. Final answer text stays buffered until verification.
The older `/chat/stream` text endpoint remains available. On disconnect, execution
stops cooperatively at the next progress boundary; an already-running model or
shell request may finish before cleanup. The service stays busy until it exits.
Command approval still happens in the process running the service.

See [resource profiles](docs/resource-profiles.md) for budget presets and
[release validation](docs/releasing.md) for the test and packaging workflow.
