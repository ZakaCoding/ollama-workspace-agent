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

### Changed

- Extracted shared chat, indexing, status, and reset operations into `AgentService` for CLI and API reuse.
- Code-review findings now include exact source evidence for easier verification.
- Added initial FastAPI endpoints for health, status, chat, and indexing.
- FastAPI now loads `.env`, exposes `POST /clear`, and returns clear errors for chat and indexing failures.
- Added plain-text streaming through `POST /chat/stream` for conversational responses.
- Added optional API-key protection for non-health FastAPI endpoints.
- Added direct and API-backed CLI modes with streamed API chat responses.
- Simplified the CLI presentation into a compact lightweight terminal interface.

## [0.1.0] - 2026-08-27

### Added

- Initial project structure with the CLI entry point and application tools.
