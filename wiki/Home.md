# Local Coding Agent Wiki

A public technical guide to this repository: a small Python coding assistant that connects to an OpenAI-compatible Ollama endpoint and operates on a bounded local workspace through explicit tools.

The project is useful in two ways:

- **For developers:** a compact reference implementation for tool-calling agents, workspace boundaries, and local code search.
- **For AI research:** a concrete sandbox for studying how an agent plans, selects tools, observes results, verifies work, and maintains task-local state.

## Start here

- [Getting Started](Getting-Started.md): install dependencies, configure Ollama, and run the CLI.
- [Architecture](Architecture.md): understand the runtime and module boundaries.
- [Tools](Tools.md): inspect the tool contract exposed to the model.
- [Indexing and Search](Indexing-and-Search.md): build and query the local semantic code index.
- [Safety and Guardrails](Safety-and-Guardrails.md): understand workspace isolation and confirmation behavior.
- [Development](Development.md): test, extend, and troubleshoot the project.
- [Research Notes](Research-Notes.md): research questions, limitations, and possible experiments.

## Project status

This is an early, intentionally inspectable implementation. It favors straightforward Python modules over a large framework. The current agent can inspect files, write files, run approved workspace commands, inspect Git state, and search an embedding-backed code index.

The local index and environment file are machine-local artifacts. They are not part of the source history.

## Design principles

1. Keep the model behind a narrow, inspectable tool interface.
2. Resolve filesystem paths against one workspace root.
3. Give each user request fresh task state.
4. Verify important boundaries with tests.
5. Prefer local, reproducible components where practical.
6. Make limitations visible instead of presenting a prototype as a production system.
