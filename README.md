# Local Coding Agent

A small Python CLI coding assistant that connects to a remote Ollama server and can inspect or operate on the project workspace through registered tools.

## Requirements

- Python 3.11+
- Ollama running on a reachable machine
- A model installed on Ollama, such as `ornith:9b`

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install python-dotenv requests
```

Create `.env` in the project root:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=ornith:9b
```

For the current remote Tailscale setup:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=ornith:9b
```

Keep `.env` private. It is excluded from Git by `.gitignore`.

## Verify Ollama

From the agent machine:

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

A successful response contains a `models` list.

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
│   ├── llm/         OpenAI-compatible Ollama client
│   └── tools/       Workspace tool implementations and registry
├── demo/            Small demo code
├── main.py          CLI entry point
├── CHANGELOG.md     Project change history
└── README.md        Project documentation
```

## Development Check

Compile the Python modules with:

```bash
python -m py_compile main.py app/agent/__init__.py app/agent/core.py app/llm/client.py app/tools/basic.py app/tools/registry.py
```
