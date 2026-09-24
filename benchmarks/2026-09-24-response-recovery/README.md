# Response recovery regression results

The saved conversation showed an assistant-status question entering the tool
loop, accumulating 111,810 characters of tool results, then repeating calculator
examples from repository fixtures. The fixes route social/status messages without
old task context, bound tool evidence, reject repeated narration, and detect
truncated model responses. No model upgrade was required for the passing checks.

Python 3.12 validation: **400 tests passed**. Routing unit tests now stub search
so a local index cannot make them depend on the live embedding server.

| Evaluation segment | Passed / attempted | Notes |
| --- | ---: | --- |
| Initial Ornith 9B | 10/10 | Before final search formatting and greeting refinements |
| Initial Qwen 7B | 6/10 | Search/context failures retained |
| Intermediate Qwen search | 1/2 | Revealed citation header clipping |
| Final Qwen core regressions | 10/10 | Five cases, twice each |
| Final Qwen greeting follow-up | 2/2 | `hi then` after a project discussion |
| Final Ornith rerun | 0/1 | Two failed requests; stopped after 120 seconds |

The final Ornith rerun planned six cases but stopped after an infrastructure
failure on the first. It does not establish final-source Ornith quality. The
earlier successful Ornith run is not a substitute for that missing validation.
The passing live runs were captured September 22; the final test run and Ornith
timeout were captured September 24. These are focused fixtures, not a full
general coding benchmark.

Core cases: assistant status with the original history replayed in a disposable
workspace, a large legacy search result, read-only inspection, legacy search,
and editing. Final Qwen checks preserve source headers and the relevant tail
under a 2,000-character evidence budget. Greeting cases use no tools.

[Summary](summary.json) and per-segment JSON files retain outcomes and error
diagnostics, including failed attempts. They omit conversation bodies and full
event traces; original detailed traces remain locally under `.owa/`. The private
history backup remains `.owa/history-before-response-fix.json`. Its hash is
recorded in replay outcomes; the history itself is not published here.
[Source hashes](source-hashes.json) identify the final runtime and evaluator.

Reproduce focused checks with an installed model and configured Ollama access:

```bash
.venv312/bin/python -m pytest -q
.venv312/bin/python scripts/eval-agent.py --model qwen2.5-coder:7b \
  --cases assistant_status greeting_followup large_tool_context legacy_search edit read_only \
  --repeat 2 --output .owa/response-regressions.json
```

Add `--history-fixture .owa/history-before-response-fix.json` for the local
private-history replay. Without it, the evaluator uses synthetic old history.
