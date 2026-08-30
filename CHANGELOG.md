# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-08-28

### Added

- Initial local coding assistant CLI.
- Ollama chat integration using `LLM_BASE_URL` and `LLM_MODEL`.
- Workspace tools for listing directories, reading files, writing files, and executing safe shell commands.
- Calculator tools for basic arithmetic operations.
- Semantic code indexing and search through the new `search_code` tool.
- Local project index storage under `.ai/`, excluded from version control.
- OpenAI-compatible LLM client with request diagnostics and forced tool calls for protocol verification.
- Agent runtime guardrails for workspace-aware execution and per-task state isolation.

### Fixed

- Restored the missing `Agent` class so `main.py` can import and start the application.
- Connected the agent to the existing tool registry and Ollama tool-calling responses.
- Wired `main.py` to the package-based agent implementation.
- Hardened filesystem and shell boundaries so commands cannot escape the workspace.
- Removed stale task requirement state from previous requests and ensured a fresh `AgentState` per user prompt.
- Normalized environment-variable documentation to use placeholders instead of concrete host addresses.
- Enforced read-only behavior for questions so file writes and shell commands are blocked at runtime.
- Routed implementation questions through semantic search and file verification before producing an answer.
- Prevented additional tool calls after required retrieval and verification are complete.

## [Unreleased]

### Added

- Added client-side tool-call validation so unavailable tools are rejected before execution.
- Added a bounded context builder for formatting semantic-search results for the LLM.
- Added client-side evidence notes for unsupported completion claims.
- Added `/help`, `/index`, `/status`, `/clear`, and `/quit` CLI commands.
- Added a read-only Python code-review tool with structured security findings.
- Added `patch_file` tool for targeted search-and-replace edits without rewriting the whole file.
- Added `pyproject.toml` with `owa` as an installable CLI entry point.
- Added `app/cli.py` as the main CLI module, with `main.py` as a thin shim for `python main.py`.
- Added `app/config.py` for central config path resolution (`~/.config/owa/.env`).
- Added `/setup` command — interactive wizard to configure Ollama host, models, and API key.
- Added auto-index on startup when no `.ai/index.db` exists in the current project.

### Changed

- Extracted shared chat, indexing, status, and reset operations into `AgentService` for CLI and API reuse.
- Code-review findings now include exact source evidence for easier verification.
- Added initial FastAPI endpoints for health, status, chat, and indexing.
- FastAPI now loads `.env`, exposes `POST /clear`, and returns clear errors for chat and indexing failures.
- Added plain-text streaming through `POST /chat/stream` for conversational responses.
- Added optional API-key protection for non-health FastAPI endpoints.
- Added direct and API-backed CLI modes with streamed API chat responses.
- Renamed project to **OwA — Ollama Workspace Agent**.
- Overhauled CLI with `rich`: branded banner, styled prompt, dot spinner, Markdown-rendered responses, and colored error/status messages.
- Removed debug output (`>>> LLM REQUEST`, `STATUS`, `TOOL CALLS`) from `LLMClient`.
- Changed `tool_choice` from `required` to `auto` so the model only calls tools when needed.
- Replaced bare `print()`/`input()` in agent core and shell tool with `rich` styled output.
- `patch_file` and `write_file` are now both blocked on read-only tasks and tracked in `AgentState`.
- System prompt updated to reflect OwA identity and prefer `patch_file` over `write_file` for modifications.
- Config loads from `~/.config/owa/.env` globally, with per-project `.env` override.
- Removed `load_dotenv()` from `app/indexer/embeddings.py` — config is now loaded centrally.

### Fixed

- `run_command` confirmation prompt now uses `rich` `Confirm.ask()` instead of bare `input()`.
- Blocked tool warnings now surface as styled yellow messages instead of raw stdout noise.

## [0.1.0] - 2026-08-27

### Added

- Initial project structure with the CLI entry point and application tools.
