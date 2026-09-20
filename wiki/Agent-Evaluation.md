# Live agent evaluation

Unit tests check orchestration with controlled model responses. To check an
actual installed Ollama model, run from the repository root:

```bash
python scripts/eval-agent.py --model qwen2.5-coder:7b --output .owa/eval.json
```

The script reads the repository `.env` for the Ollama connection and embedding
settings. Export `ALL_PROXY=socks5h://127.0.0.1:1055` first if your server requires
the Tailscale proxy. It does not download models or change the configured model.

Each case runs in a separate process and temporary workspace, with a 240-second
timeout. The report includes the response, executed tool calls and results,
errors, request metrics, and elapsed time. The command exits nonzero if any case
fails. Retrieval timing excludes initial fixture indexing.

| Case | Pass requirement |
| --- | --- |
| Greeting after unrelated code history | Short greeting, no tool calls or copied script |
| Read a source file | Actual `read_file` execution and correct description |
| Locate a function | Citation to the correct indexed source file |
| Fix a subtraction bug | Actual patch, actual passing test command, independent passing test run |

Fixture files must remain unchanged except for the intended calculator edit.
Only the fixture's exact `python -m unittest -q` command is automatically
approved; all other generated commands are rejected. Ordinary OwA command
confirmation behavior remains unchanged.

These are smoke tests for basic agent behavior, not proof of reliability on
large repositories or complex changes. The text tool-call compatibility adapter
accepts only a complete JSON call, optionally inside a recognized envelope;
prose, scripts, and invented test output are never executed. The normal tool
allowlist, argument validation, and workspace checks still apply.

On 2026-09-20, the installed `qwen2.5-coder:7b` (7.6B, Q4_K_M) and
`ornith:9b` (9B, Q4_K_M) both passed all four cases after the orchestration fixes.
The verified edit took about 5 seconds and 13 seconds respectively in those runs.
Latency includes model requests and depends on model loading and server load;
these timings are observations, not performance guarantees.
