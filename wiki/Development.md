# Development

## Repository layout

```text
.
├── app/
│   ├── agent/       Agent orchestration, state, context trimming, session memory
│   ├── indexer/     Chunking, embeddings, SQLite storage, and search
│   ├── llm/         Ollama-compatible chat client
│   ├── tools/       Tool implementations and registry
│   ├── api.py       FastAPI endpoints
│   ├── api_client.py  HTTP client for API mode
│   ├── cli.py       CLI entry point — banner, prompt loop, commands
│   ├── config.py    Global config path (~/.config/owa/.env)
│   └── service.py   Shared service layer for CLI and API
├── tests/           Pytest test suite
├── wiki/            Project documentation
├── main.py          Thin shim — delegates to app/cli.py
├── pyproject.toml   Package metadata and entry point
├── CHANGELOG.md     Version history
├── RELEASE.md       Release process guide
└── TODO.md          Feature backlog
```

## Install for development

```bash
git clone https://github.com/ZakaCoding/ollama-workspace-agent
cd ollama-workspace-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
python main.py
# or
owa
```

## Test

```bash
pytest tests/ -v
```

## Compile check

```bash
python -m py_compile main.py app/agent/*.py app/indexer/*.py app/llm/*.py app/tools/*.py app/cli.py app/service.py app/api.py
```

## Contributing

Contributions are welcome. A few guidelines:

- Keep modules small with explicit inputs and outputs.
- Keep public tool names stable once documented.
- Add tests for behavior at the boundary, not implementation details.
- For a new external dependency: document required env vars, provide a useful failure message when unavailable, and add a test that works without a live Ollama server.

## Review checklist

- Does the change preserve workspace isolation?
- Are failures and unavailable services handled explicitly?
- Does the model receive a precise schema and useful result text?
- Are generated files (`.owa/`, `dist/`, `*.egg-info`) gitignored?
- Are tests and wiki updated?
- Does the change work without a live Ollama server where possible?

## Release process

See [RELEASE.md](../RELEASE.md) for the full release steps. Short version:

1. Bump `version` in `pyproject.toml`
2. Add entry to `CHANGELOG.md`
3. `git commit` and `git push`
4. `git tag vX.Y.Z && git push origin vX.Y.Z`

The publish workflow builds and uploads to PyPI automatically on version tags.
