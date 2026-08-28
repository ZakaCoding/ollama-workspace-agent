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
python -m pip install python-dotenv requests httpx pytest
```

Create `.env` in the project root:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=ornith:9b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
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

Enter a request at the `You` prompt. Use `exit`, `quit`, `/exit`, or `/quit` to stop.

## Tools

The agent can call these workspace tools:

- `list_dir`: list files and directories
- `read_file`: read UTF-8 text files
- `run_command`: run a shell command after confirmation

The current development phase forces tool calls when tools are supplied so the Ollama tool-calling protocol can be verified.

## Project Layout

```text
.
├── app/
│   ├── agent/       Agent orchestration and system prompt
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
