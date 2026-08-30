Licensed under the MIT License. See [LICENSE](LICENSE) for details.

# OwA — Ollama Workspace Agent

OwA is an open-source local coding assistant built for developers who want AI help without sending their code, prompts, or context to a cloud service.

It runs on your own hardware, works with Ollama, and is designed specifically for local-first workflows. The idea is simple: the model runs on your machine, your repository stays on your machine, and the agent works inside your workspace with explicit boundaries.

## Why OwA exists

Most chat agents are designed for cloud-hosted models and remote infrastructure. That works well for large teams and expensive backends, but it is not a natural fit for developers who want a private, local coding assistant.

OwA was built for a different workflow:

- local hardware instead of paid cloud inference
- small models such as `ornith:9b` and `qwen2.5-coder`
- project-aware assistance without leaving the workspace
- an inspectable, open-source agent with explicit safety boundaries
- a coding tool that respects local ownership of the codebase

The project intentionally keeps the architecture small and readable so developers can understand what is happening and extend it without a huge framework or hidden runtime.

## What it does

- indexes the workspace for semantic code search
- reads, writes, and patches files inside the active project
- inspects Git state, diff, and recent commit history
- runs shell commands only after explicit confirmation
- reviews Python files for common security issues
- persists session memory across conversations
- works as both a CLI and a local FastAPI API

## Tech stack

OwA is intentionally lightweight and practical:

- Python 3.11+
- Ollama for local chat and embedding models
- FastAPI and Uvicorn for the local HTTP API
- SQLite for the local code index
- Rich for terminal UX and feedback
- requests and httpx for service calls
- semantic indexing and retrieval over project files

## Recommended models

OwA is designed to work well with local models such as:

- `llama3.1:8b`
- `qwen2.5-coder`
- `ornith:9b`
- `nomic-embed-text`

The project is purpose-built for realistic local developer setups instead of assuming a high-end GPU or an always-on cloud service.

## Install

```bash
pip install ollama-workspace-agent
```

Or use pipx for an isolated environment:

```bash
pipx install ollama-workspace-agent
```

## Quick start

```bash
cd your-project
owa
```

On first run, use `/setup` to configure your Ollama connection. OwA will save the settings in `~/.config/owa/.env` and then index the project on startup.

## Configuration

```env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=llama3.1:8b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
API_KEY=choose-a-private-api-key
```

You can also place a local `.env` in the project root to override the global config for a specific repository.

## Verify Ollama

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

Then pull the models you want to use:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## CLI commands

| Command | Description |
| --- | --- |
| `/setup` | Configure provider and model settings |
| `/model` | Switch the active chat model |
| `/index` | Rebuild the project index |
| `/status` | Show index and workspace status |
| `/clear` | Clear session memory |
| `/help` | Show available commands |
| `/quit` | Exit |

## Local security and guardrails

OwA keeps execution inside a bounded workspace and requires explicit confirmation before shell commands. The project is not a permission system, but it is designed to make accidental workspace escapes and destructive actions harder.

For a detailed breakdown, see [Safety and Guardrails](wiki/Safety-and-Guardrails.md).

## Documentation

- [Home](wiki/Home.md) — project overview and mission
- [Getting Started](wiki/Getting-Started.md) — install, configure, and run
- [Architecture](wiki/Architecture.md) — runtime flow and module boundaries
- [Tools](wiki/Tools.md) — tool contract and behavior
- [Indexing and Search](wiki/Indexing-and-Search.md) — local semantic retrieval design
- [Safety and Guardrails](wiki/Safety-and-Guardrails.md) — boundaries and safe operations
- [Development](wiki/Development.md) — repo layout and contribution workflow
- [Research Notes](wiki/Research-Notes.md) — experiments and open questions

## Support the project

OwA is open source and built for the long tail of local developers who want AI help without giving up privacy or control.

If this project helps you, please consider sponsoring the work that keeps it maintained, documented, and improved.

- GitHub Sponsors: https://github.com/sponsors/ZakaCoding

## Links

- [PyPI](https://pypi.org/project/ollama-workspace-agent/)
- [GitHub](https://github.com/ZakaCoding/ollama-workspace-agent)
- [Changelog](CHANGELOG.md)
- [License](LICENSE)

## Project status

Active development. The goal is to keep the project useful, inspectable, and grounded in real local developer workflows instead of cloud-first assumptions.

Contributions, issue reports, and sponsor support are welcome.
