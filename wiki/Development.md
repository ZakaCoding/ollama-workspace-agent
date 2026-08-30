# Development

OwA is intentionally small and easy to inspect. The main goal of the codebase is clarity: local-first design, bounded tools, and a small enough surface area that contributors can understand the runtime quickly.

## Repository layout

```text
.
├── app/
│   ├── agent/       agent orchestration, state, and verification
│   ├── api.py       FastAPI endpoints
│   ├── cli.py       interactive CLI app
│   ├── config.py    env and config resolution
│   ├── service.py   shared runtime services
│   ├── indexer/     embedding, chunking, and search logic
│   ├── llm/         Ollama-compatible client
│   ├── memory/      reserved for future memory work
│   └── tools/       tool implementations and registry
├── demo/            example or demo code
├── tests/           pytest suite
├── wiki/            project documentation
├── main.py          project entry point
├── CHANGELOG.md     release notes
├── README.md        repository overview
├── LICENSE          MIT license
└── pyproject.toml   packaging metadata and scripts
```

## Local setup

```bash
git clone https://github.com/ZakaCoding/ollama-workspace-agent
cd ollama-workspace-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Validation commands

```bash
PYTHONPATH=. pytest -q
python -m compileall -q main.py app tests
python -m py_compile main.py app/agent/core.py app/llm/client.py app/tools/registry.py
```

Focus on a single test area when iterating:

```bash
PYTHONPATH=. pytest -q tests/test_agent_guardrails.py
PYTHONPATH=. pytest -q tests/test_calculator.py
```

## Contribution expectations

When contributing, prefer small, explicit modules and clear boundaries. This project works best when changes are understandable without a large architectural rewrite.

Good contribution patterns:

- keep tool contracts explicit and stable
- add tests for behavior at the boundary
- document new env vars and config options
- preserve workspace isolation and approval flow
- keep code review and agent guardrails in mind

## Before merging a change

Check the following:

- does it preserve the workspace boundary?
- does it introduce hidden side effects?
- does it fail gracefully when Ollama or a model is unavailable?
- are docs updated where the user-facing behavior changed?
- are tests and validation commands still passing?

## Troubleshooting

Use Git status and diff checks when reviewing changes:

```bash
git status --short --branch
git diff --check
```

Avoid sharing raw logs if they contain private hostnames, repo paths, or user prompts.
