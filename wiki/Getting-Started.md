# Getting Started

OwA is designed to feel lightweight and local-first. This guide covers the fastest path from install to a working project-aware agent.

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com) running on a reachable machine
- a local chat model such as `llama3.1:8b` or `qwen2.5-coder`
- an embedding model such as `nomic-embed-text`

## Install

Use pipx if you want an isolated install:

```bash
pipx install ollama-workspace-agent
```

Or install straight with pip:

```bash
pip install ollama-workspace-agent
```

## Configure the agent

The interactive setup flow is the easiest path:

```bash
cd your-project
owa
```

Then type `/setup`. OwA will guide you through the Ollama host, chat model, embedding model, and optional API key.

You can also configure it manually in `~/.config/owa/.env`:

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=llama3.1:8b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
API_KEY=choose-a-private-api-key
```

A project-local `.env` file can override the global config for a specific repository. This is useful when you work across many projects or want a per-project configuration.

## Verify Ollama

Check that the local API is responding:

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

Pull the models you need before the first run:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Run the agent

From the project you want help with:

```bash
cd your-project
owa
```

On the first run, OwA will index the project automatically. After that, you can start asking questions, asking it to edit files, or run workspace-safe review tasks.

## Useful commands

| Command | Purpose |
| --- | --- |
| `/setup` | Configure or reconfigure Ollama settings |
| `/model` | Switch the active LLM |
| `/index` | Rebuild the project index |
| `/status` | Show local workspace status |
| `/clear` | Clear previous conversation state |
| `/help` | List commands |
| `/quit` | Exit |

## Excluding files from indexing

Create a `.owaignore` file in the project root if you want to skip certain folders or files:

```text
# .owaignore
secrets.json
fixtures/
*.min.js
```

Common project directories such as `.git`, `.venv`, `node_modules`, and build folders are ignored automatically.

## Troubleshooting

### `owa: command not found`

Make sure your Python environment is activated or that the pipx binary directory is on your PATH.

### Embedding or model connection fails

Check that Ollama is running and that the host values in your config match the machine where Ollama is listening.

### No search results

Run `/index` again to rebuild the local index. If the project changed significantly, a full re-index is often the fastest fix.

### Setup keeps showing the old host

That is expected; the config is loaded from the saved local settings and reused as the default.
