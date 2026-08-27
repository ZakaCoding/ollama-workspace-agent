# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Added

- Initial local coding assistant CLI.
- Ollama chat integration using `OLLAMA_URL` and `OLLAMA_MODEL`.
- Workspace tools for listing directories, reading files, and running commands.
- OpenAI-compatible LLM client with request diagnostics and forced tool calls for
	protocol verification.

### Fixed

- Restored the missing `Agent` class so `main.py` can import and start the application.
- Connected the agent to the existing tool registry and Ollama tool-calling responses.
- Wired `main.py` to the package-based agent implementation.
- Corrected the remote Tailscale endpoint and standardized the `LLM_BASE_URL` and
	`LLM_MODEL` environment variables.

## [0.1.0] - 2026-08-27

### Added

- Initial project structure with the CLI entry point and application tools.
