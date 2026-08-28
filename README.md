Licensed under the MIT License. See [LICENSE](LICENSE) for details.

# Local Coding Agent

A small Python CLI coding assistant that connects to a remote Ollama server and can inspect or operate on the project workspace through registered tools.

## Requirements

- Python 3.11+
- Ollama running on a reachable machine
- A chat model installed on Ollama, such as `ornith:9b`
- An embedding model installed on Ollama, such as `nomic-embed-text`

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install python-dotenv requests httpx pytest fastapi uvicorn
```

Create `.env` in the project root:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=ornith:9b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
API_KEY=choose-a-private-api-key
```

Keep `.env` private. It is excluded from Git by `.gitignore`.

`LLM_BASE_URL` uses Ollama's OpenAI-compatible `/v1` API. `EMBEDDING_BASE_URL`
uses Ollama's native `/api/embed` API. If Ollama runs on the same machine,
replace `YOUR_OLLAMA_HOST` with `127.0.0.1`.

## Verify Ollama

From the agent machine:

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

A successful response contains a `models` list.

Make sure the models named in `.env` are installed on that Ollama server. For
example:

```bash
ollama pull ornith:9b
ollama pull nomic-embed-text
```

If `ollama` is not installed locally, install the models through the Ollama
machine's normal administration workflow instead.

## Run

```bash
source .venv/bin/activate
python main.py
```

Enter a request at the `›` prompt. Available commands are `/help`, `/index`,
`/status`, `/clear`, and `/quit`.

The CLI uses a compact terminal layout and prints the active mode on startup.

To use the CLI as a client for the FastAPI server:

```bash
python main.py --api-url http://127.0.0.1:8000
```

In API mode, chat responses stream through `/chat/stream`. Set `API_KEY` in
`.env` or pass `--api-key` when the server requires authentication.

Run the HTTP API with:

```bash
uvicorn app.api:app --host 127.0.0.1 --port 8000
```

The API loads `.env` automatically and provides `GET /health`, `GET /status`,
`POST /chat`, `POST /chat/stream`, `POST /clear`, and `POST /index`. Chat
requests use `{"message": "your request"}`. Use `/chat/stream` for plain-text
streaming; use `/chat` for tool-enabled agent tasks.

When `API_KEY` is configured, include it in the `X-API-Key` header for every
endpoint except `/health`.

## Tools

The agent can call these workspace tools:

- `list_dir`: list files and directories
- `read_file`: read UTF-8 text files
- `code_review`: review Python files for common security risks
- `run_command`: run a shell command after confirmation

The current development phase forces tool calls when tools are supplied so the Ollama tool-calling protocol can be verified.

## Project Layout

```text
.
├── app/
│   ├── agent/       Agent orchestration and system prompt
│   ├── api.py        FastAPI endpoints and request models
│   ├── service.py    Shared chat, indexing, and status service
│   ├── indexer/     Code indexing and semantic search
│   ├── llm/         OpenAI-compatible Ollama client
│   └── tools/       Workspace tool implementations and registry
├── demo/            Small demo code
├── main.py          CLI entry point
├── CHANGELOG.md     Project change history
└── README.md        Project documentation
```

## Development Check

Verify the environment before starting the interactive CLI:

```bash
python -c "import dotenv, requests, httpx; print('Dependencies OK')"
```

Compile the Python modules with:

```bash
python -m py_compile main.py app/agent/*.py app/indexer/*.py app/llm/*.py app/tools/*.py
```
