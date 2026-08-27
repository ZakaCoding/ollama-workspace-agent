# Development

## Repository layout

```text
.
├── app/
│   ├── agent/       Agent orchestration, state, and verification
│   ├── indexer/     Chunking, embeddings, SQLite storage, and search
│   ├── llm/         Ollama-compatible chat client
│   ├── memory/      Reserved package for future memory work
│   └── tools/       Tool implementations and registry
├── demo/            Small demonstration code
├── tests/           Pytest coverage for guardrails and calculator behavior
├── main.py          Interactive CLI entry point
└── wiki/            Public project documentation
```

## Test and validation commands

From the repository root with the virtual environment active:

```bash
PYTHONPATH=. pytest -q
python -m compileall -q main.py app tests
python -m py_compile main.py app/agent/core.py app/llm/client.py app/tools/registry.py
```

Run focused tests while working on one area:

```bash
PYTHONPATH=. pytest -q tests/test_agent_guardrails.py
PYTHONPATH=. pytest -q tests/test_calculator.py
```

## Adding code

Prefer small modules with explicit inputs and outputs. Keep public tool names stable once documented. Add tests for behavior at the boundary rather than testing implementation details that do not matter to callers.

For a new external dependency:

1. Add it to the setup documentation and project dependency metadata when available.
2. Document required environment variables.
3. Provide a useful failure message when the service is unavailable.
4. Add a test that does not require the external service for ordinary CI.

## Review checklist

- Does the change preserve workspace isolation?
- Does it create or expose new side effects?
- Are failures and unavailable services handled explicitly?
- Does the model receive a precise schema and useful result text?
- Are generated files ignored?
- Are tests and documentation updated?
- Does the change work without a live Ollama server where possible?

## Troubleshooting

Inspect the current state with:

```bash
git status --short --branch
git diff --check
```

The agent prints request URL, model, status, and tool-call diagnostics. Avoid sharing those logs publicly if they contain private hostnames or prompts.
