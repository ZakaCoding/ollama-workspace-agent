# Changelog

All notable changes to this project are documented here.

## [Unreleased]

## [0.3.1] - 2026-08-29

### Fixed

- Embedding config (`EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`) was read at module import time, before `load_dotenv()` ran, causing `/index` to always connect to `127.0.0.1` and fail with `Connection refused`.

## [0.3.0] - 2026-08-29

### Added

- `owa` installable CLI command via `pyproject.toml`.
- `app/cli.py` as the main CLI module — `main.py` is now a thin shim.
- `app/config.py` for central config resolution (`~/.config/owa/.env`).
- `/setup` command — interactive wizard to configure Ollama host, models, and API key.
- Auto-index on startup when no `.ai/index.db` exists in the current project.
- `patch_file` tool for targeted search-and-replace edits without rewriting the whole file.
- GitHub Actions CI workflow — compile check and tests on every push and PR.
- GitHub Actions publish workflow — builds and publishes to PyPI on version tags.

### Changed

- Renamed project to **OwA — Ollama Workspace Agent**.
- Overhauled CLI with `rich`: branded banner, styled prompt, dot spinner, Markdown-rendered responses, and colored error/status messages.
- Removed debug output (`>>> LLM REQUEST`, `STATUS`, `TOOL CALLS`) from `LLMClient`.
- Changed `tool_choice` from `required` to `auto` so the model only calls tools when needed.
- Replaced bare `print()`/`input()` in agent core, shell tool, and indexer with `rich` styled output.
- `patch_file` and `write_file` are both blocked on read-only tasks and tracked in `AgentState`.
- System prompt updated to reflect OwA identity and prefer `patch_file` over `write_file` for modifications.
- Config loads from `~/.config/owa/.env` globally, with per-project `.env` override.
- Extracted shared chat, indexing, status, and reset operations into `AgentService` for CLI and API reuse.
- Added FastAPI endpoints: `GET /health`, `GET /status`, `POST /chat`, `POST /chat/stream`, `POST /clear`, `POST /index`.
- Added optional API-key protection for non-health FastAPI endpoints.
- Added direct and API-backed CLI modes with streamed API chat responses.

### Fixed

- `run_command` confirmation prompt now uses `rich` `Confirm.ask()` instead of bare `input()`.
- Blocked tool warnings now surface as styled yellow messages instead of raw stdout noise.
- Indentation error in `indexer/index.py`.
- Removed `load_dotenv()` from `app/indexer/embeddings.py` — config is now loaded centrally.

## [0.2.0] - 2026-08-28

### Added

- Initial local coding assistant CLI.
- Ollama chat integration using `LLM_BASE_URL` and `LLM_MODEL`.
- Workspace tools: `list_dir`, `read_file`, `write_file`, `run_command`.
- Semantic code indexing and search through the `search_code` tool.
- Local project index storage under `.ai/`, excluded from version control.
- OpenAI-compatible LLM client with forced tool calls for protocol verification.
- Agent runtime guardrails for workspace-aware execution and per-task state isolation.
- Git tools: `git_status`, `git_diff`, `git_log`.
- Read-only Python code-review tool with structured security findings.
- Client-side tool-call validation so unavailable tools are rejected before execution.

### Fixed

- Hardened filesystem and shell boundaries so commands cannot escape the workspace.
- Enforced read-only behavior for questions so file writes and shell commands are blocked.
- Routed code questions through semantic search and file verification before answering.

## [0.1.0] - 2026-08-27

### Added

- Initial project structure with CLI entry point and application tools.
