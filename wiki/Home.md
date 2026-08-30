# OwA — Ollama Workspace Agent

OwA is an open-source local coding assistant designed for developers who want AI help without giving up privacy, control, or ownership of their code.

The project is built around a simple idea: the model runs on your machine, the code stays on your machine, and the agent works inside the current workspace instead of pretending to be a remote cloud service.

## Why build OwA?

Most coding agents are optimized for large cloud-hosted models and remote tool execution. That makes sense for some teams, but it is a poor fit for local-first development.

OwA was built for developers who:

- run Ollama locally
- prefer smaller models over large hosted services
- want code-aware assistance without exposing repos to the cloud
- need transparent and inspectable agent behavior
- work with modest hardware and still want useful AI help

The result is a project that is intentionally simple: explicit tools, local indexing, clear boundaries, and a direct connection to the developer's repo.

## What OwA does

- indexes the project for context-aware semantic search
- reads, writes, and patches files inside the workspace
- checks Git state, diff, and recent history
- allows shell actions only after clear confirmation
- reviews code for common security issues in Python
- keeps conversation state local to the project and user profile
- offers both CLI and API usage patterns

## Who it is for

OwA is especially useful for:

- solo developers working on local repositories
- people using Ollama with 4–9B models or similar hardware
- developers who want a coding agent that is easier to inspect and reason about
- teams building private workflows without external API keys or cloud dependencies

## Tech stack

OwA combines a small set of practical components:

- Python 3.11+
- Ollama for local chat and embeddings
- SQLite for local project indexing
- FastAPI and Uvicorn for the local API layer
- Rich for the terminal interface
- file and Git tools for workspace-aware execution

## Documentation

- [Getting Started](Getting-Started.md) — install, configure, and run
- [Architecture](Architecture.md) — runtime flow and module layout
- [Tools](Tools.md) — available tools and safety boundaries
- [Indexing and Search](Indexing-and-Search.md) — how the project index works
- [Safety and Guardrails](Safety-and-Guardrails.md) — workspace isolation and approval flow
- [Development](Development.md) — contribution and validation workflow
- [Research Notes](Research-Notes.md) — experiments and open questions

## Install

```bash
pip install ollama-workspace-agent
```

Or with pipx:

```bash
pipx install ollama-workspace-agent
```

Then run it inside any project:

```bash
cd your-project
owa
```

## Support

OwA is open source and built to stay useful to developers who value local-first tooling. If this project helps you, support the work that keeps it maintained and documented.

- [GitHub Sponsors](https://github.com/sponsors/ZakaCoding)

## Project status

Active development. The project is intentionally small, inspectable, and designed for real local coding work instead of heavy cloud assumptions.
