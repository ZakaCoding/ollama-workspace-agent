# Changelog

All notable changes to this project are documented here.

## [Unreleased]

### Planned

- **Multi-model support** — auto-route tasks to different models based on intent

### Known Limitations

- Emoji rendering broken with `ornith:9b` — model outputs mojibake, not an OwA bug
- `agent.stream()` does not handle tool calls — tool activity shown via stderr, final response collected then rendered

## [0.5.1] - 2026-08-31

### Changed

- **Parallel embedding** — `/index` now processes files concurrently using a `ThreadPoolExecutor` (4 workers by default). Each file's chunks are sent to Ollama in a single batched `/api/embed` request instead of one HTTP call per chunk. On large repos this reduces index time by 4–8x.
- `embed_batch()` added to `app/indexer/embeddings.py` — sends a list of texts in one request and returns all vectors.
- `_index_file()` worker function handles read → chunk → embed_batch → save for one file, enabling safe parallel execution.
- Index summary now reports `N updated, N unchanged` (and `N failed` if any errors occurred).

## [0.5.0] - 2026-08-31

### Added

- **Incremental indexing** — `/index` now skips unchanged files using SHA-256 content hashing. Only modified or new files are re-embedded. Deleted files are automatically removed from the index. Summary shows `N updated, N unchanged` after each run.
- **Better intent router** — `task_requires_code_search()` now catches a much wider range of retrieval questions: `explain`, `describe`, `find`, `list`, `show`, `search`, `summarize`, `trace`, `walk me through`, and more. Small models are kept out of the tool loop for all of these.

### Changed

- `ContextBuilder` rebuilt for small-model optimization: score threshold (`0.25`) drops irrelevant chunks, per-file cap (`2 chunks`) prevents one file dominating context, per-chunk char cap (`3000`) prevents budget overflow, `max_chars` reduced from `16000` to `12000`.
- Context retrieval fetches `10` candidates before filtering down to the best `5`, giving the per-file cap room to work.
- Context system message now injected before the user message with an explicit instruction to answer from context before exploring the filesystem.
- `ContextBuilder` instantiated once in `Agent.__init__()` instead of per-call.
- `run` in `EXPLICIT_ACTION_WORDS` — `"Run the test suite"` and similar prompts correctly route to the tool loop instead of retrieval.

## [0.4.3] - 2026-08-30

### Added

- `@filename` context — mention a file in your message with `@path/to/file` and OwA injects its content automatically.
- `/status` now shows the active chat model alongside index chunk count.

## [0.4.2] - 2026-08-30

### Added

- Project messaging and docs were refreshed around the local-first, privacy-first open-source mission.
- GitHub Pages landing page and sponsor configuration were prepared for public project discovery and funding support.

### Changed

- README and wiki now describe the project as a local Ollama-powered workspace agent built for developer workflows and small models.
- Documentation structure was tightened up to better explain install, architecture, safety boundaries, and contributor workflow.

### Fixed

- Streaming responses in direct mode now work without blocking long waits on the CLI path.
- Spinner behavior while a stream is being collected was corrected so output renders cleanly after completion.
- Ignored directories were expanded to better fit typical local developer repos and to document `.owaignore` and `/model` usage clearly.

## [0.4.1] - 2026-08-29

### Fixed

- `/model` showed wrong currewnt model on restart — env was not reloaded before reading `LLM_MODEL`.
- Model switch took effect only after restart — `LLMClient` now reads `LLM_MODEL` from env on every call instead of at init time.

## [0.4.0] - 2026-08-29

### Added

- Session memory — conversation history persists across restarts in `.owa/history.json`. Cleared with `/clear`.
- Context window management — trims to last 20 message pairs before each LLM call, keeping system prompt intact.
- `.owaignore` — place a `.owaignore` file in your project root to exclude files and directories from indexing.
- `/model` command — list available Ollama models and switch the active chat model on the fly.

## [0.3.3] - 2026-08-29

### Changed

- Renamed local index directory from `.ai/` to `.owa/` to avoid conflicts with other tools.
- On first index, `.owa/` is automatically added to the project's `.gitignore`.
- Added a tip message after first index reminding users about `.owa/` and `.gitignore`.

## [0.3.2] - 2026-08-29

### Fixed

- Missing `[project.scripts]` section header in `pyproject.toml` — `owa` entry point was not registered, causing `pipx install` to fail with "No apps associated with package".

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
