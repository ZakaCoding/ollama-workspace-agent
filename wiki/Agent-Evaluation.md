# Live agent evaluation

See the [2026-09-21 repeatability report](../benchmarks/2026-09-21/README.md)
for the full two-round results and raw traces. The
[2026-09-20 benchmark report](../benchmarks/2026-09-20/README.md) records the
original failures, fixes, and interrupted verification.

Unit tests check orchestration with controlled model responses. To check an
actual installed Ollama model, run from the repository root:

```bash
python scripts/eval-agent.py --model qwen2.5-coder:7b --output .owa/eval.json
# Repeat the full benchmark or select specific cases:
python scripts/eval-agent.py --model ornith:9b --repeat 2 --output .owa/eval-ornith.json
python scripts/eval-agent.py --model qwen2.5-coder:7b --cases direct_list command git_edit
```

The script reads the repository `.env` for the Ollama connection and embedding
settings. Export `ALL_PROXY=socks5h://127.0.0.1:1055` first if your server requires
the Tailscale proxy. It does not download models or change the configured model.

Each case runs in a separate process and temporary workspace, with a 240-second
timeout. The report includes the response, executed tool calls and results,
errors, request metrics, and elapsed time. The command exits nonzero if any case
fails. It checks server connectivity and the installed model before starting,
and stops early if every model request in a case fails. These infrastructure
failures are identified separately from agent failures. Results are saved after
each case; the terminal summary reports pass counts, median latency, tool calls,
model requests, and the planned run count. Retrieval timing excludes initial
fixture indexing. Each case is limited to eight iterations and twenty tool calls.

| Case | Pass requirement |
| --- | --- |
| Greeting after unrelated code history | Short greeting, no tool calls or copied script |
| Read a source file | Actual `read_file` execution and correct description |
| Locate a function | Citation to the correct indexed source file |
| Fix a subtraction bug | Actual patch, actual passing test command, independent passing test run |
| Learn a project | Cited current README overview without tools or embeddings |
| Search a legacy index | Actual search of a pre-FTS index and correct source description |
| Recover from failing tests | Failed test command followed by a fix and passing tests |
| Fix two source files | Both source files patched and independently passing tests |
| Learn after long unrelated history | Cited calculator overview without stale weather-app claims |
| List files directly | Actual directory listing and filenames in the answer |
| Display a file directly | Actual file read and correct description, without an index |
| Execute a command | Actual command execution with output `42` |
| Informal fix request | Understand `can u fix`, patch the source, and pass tests |
| Git status plus an edit | Execute Git status, patch the source, and pass tests |
| Create a file | Exact requested content and an actual readback |
| Security review | Execute `code_review` and identify the unsafe `eval` |
| Explain without fixing | Read the source, explain the bug, and perform no writes or commands |
| Inspect Git changes/history | Execute status, diff, and log; describe the fixture commit and pending README change |

Fixture files must remain unchanged except for the intended source edits or
requested new file. Unexpected new files and modified tests fail the case.
Only the fixture's exact `python -m unittest -q` command (or the print command
in the command case) is automatically approved; all other generated commands
are rejected. Ordinary OwA command
confirmation behavior remains unchanged.

These are smoke tests for basic agent behavior, not proof of reliability on
large repositories or complex changes. The text tool-call compatibility adapter
accepts only a complete JSON call, optionally inside a recognized envelope;
prose, scripts, and invented test output are never executed. The normal tool
allowlist, argument validation, and workspace checks still apply.

The 18 cases exercise all ten registered tools, but use small Python fixtures.
They do not establish reliability on large repositories, arbitrary commands,
external integrations, or ambiguous multi-turn requirements. Temperature is
zero; repeated runs still measure observed behavior rather than guarantee it.

On 2026-09-20, the installed `qwen2.5-coder:7b` (7.6B, Q4_K_M) and
`ornith:9b` (9B, Q4_K_M) both passed the original four cases after the orchestration fixes.
That result does not cover the five subsequently added cases.
The verified edit took about 5 seconds and 13 seconds respectively in those runs.
Latency includes model requests and depends on model loading and server load;
these timings are observations, not performance guarantees.
