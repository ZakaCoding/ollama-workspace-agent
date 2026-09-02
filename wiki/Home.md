# OwA — Ollama Workspace Agent

OwA is an open-source local coding assistant powered by Ollama. It runs entirely on your own hardware — no cloud, no telemetry, no API keys required beyond your own Ollama server.

## Why OwA?

Most chat agents struggle to work clearly with Ollama and small models (4–9B parameters). OwA was built specifically for developers who run local hardware — designed to work well with small models like `qwen2.5-coder` or `llama3.1:8b` without requiring a powerful GPU or a cloud subscription.

The idea is simple: your LLM runs on your machine, your code stays on your machine, and the agent works within your workspace. Nothing leaves your hardware.

OwA uses Ollama for both chat inference and embeddings — the full stack runs client-side.

## What it does

- Auto-indexes your project with semantic embeddings for context-aware code search
- Reads, writes, and patches files inside your workspace
- Runs shell commands with your confirmation
- Inspects Git state — status, diff, log
- Reviews Python files for common security issues
- Persists conversation history across sessions
- Trims context window automatically to keep small models stable
- Works as a direct CLI or as a FastAPI HTTP server

## Install

```bash
pipx install ollama-workspace-agent
```

Or with pip:

```bash
pip install ollama-workspace-agent
```

Then run it inside any project:

```bash
cd your-project
owa
```

## Wiki pages

- [Getting Started](Getting-Started.md) — install, configure, and run OwA
- [Architecture](Architecture.md) — runtime flow and module boundaries
- [Tools](Tools.md) — workspace tools exposed to the model
- [Indexing and Search](Indexing-and-Search.md) — how the local code index works
- [Safety and Guardrails](Safety-and-Guardrails.md) — workspace isolation and confirmation behavior
- [Development](Development.md) — contributing, testing, and extending OwA
- [Research Notes](Research-Notes.md) — open questions, experiments, and live self-run observations
- [Journey](../JOURNEY.md) — a narrative record of OwA running inside its own repository

## Design principles

1. Keep the model behind a narrow, inspectable tool interface.
2. Resolve filesystem paths against one workspace root.
3. Give each user request fresh task state.
4. Verify important boundaries with tests.
5. Prefer local, reproducible components where practical.
6. Make limitations visible rather than hiding them.

## Links

- [PyPI](https://pypi.org/project/ollama-workspace-agent/)
- [GitHub](https://github.com/ZakaCoding/ollama-workspace-agent)
- [Changelog](https://github.com/ZakaCoding/ollama-workspace-agent/blob/main/CHANGELOG.md)
- [Landing Page](https://zakacoding.github.io/ollama-workspace-agent)
