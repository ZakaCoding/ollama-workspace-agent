# OwA agent benchmark — 2026-09-20

Live testing reproduced seven distinct failures and drove two implementation
commits: `9113bd2` (tool routing) and `a339b78` (command ordering and workspace
paths). All **312 automated tests pass**. The final live matrix is **incomplete**
because the Ollama connection dropped; the partial results below are not a
claim of an 18/18 pass or repeatability.

## Observed results

| Stage | Passed / completed cases | Median task time | Raw traces |
| --- | ---: | ---: | --- |
| Qwen baseline (original 9 + routing 8) | 12/17 | 3.20 s | [qwen-baseline.json](qwen-baseline.json) |
| Qwen intermediate routing fixes | 7/8 | 3.21 s | [qwen-routing-intermediate.json](qwen-routing-intermediate.json) |
| Ornith discovery round | 16/18 | 11.79 s | [ornith-discovery.json](ornith-discovery.json) |
| Ornith final fixes, interrupted round | 10/10 | 9.40 s | [ornith-after-partial.json](ornith-after-partial.json) |

The rows cover different case sets and implementation stages; their aggregate
pass counts and latencies are not directly comparable. The final Ornith run
completed the first ten cases only. It passed recovery and multi-file editing,
the two failures from its discovery round. The remaining eight cases and the
second round were not completed. Qwen's intermediate run predates the final
Git tool selection and command-order/path fixes; a full final Qwen rerun is
still required. No current Ornith-versus-Qwen speed ranking is established.

## Reproduced failures and changes

| Failure | Change | Evidence |
| --- | --- | --- |
| Direct directory listing became an indexed question | Route explicit inspections to tools without an index | Qwen `direct_list`: fail → pass |
| Direct file display became an indexed question | Preserve direct file-read intent | Qwen `direct_read`: fail → pass |
| Plain execution lacked the command tool | Expose execution tools for explicit commands and require actual execution | Qwen `command`: fail → pass |
| `can u fix` did not authorize the requested edit | Recognize common request prefixes | Qwen `polite_edit`: fail → pass |
| Git mentions hid editing tools; broad Git selection then wasted turns | Combine requested Git inspection with editing tools and narrow Git selection | Initial Qwen `git_edit` failure; intermediate run fixed/tested but exhausted its budget; corrected Git selection has regression coverage |
| Agent fixed before running the requested failing test | Withhold editing tools until the initial command runs | Ornith `recovery`: fail → pass |
| Absolute workspace paths and redundant `cd` wasted the iteration budget | Normalize only in-workspace paths and clarify command working directory | Ornith `multi_file`: fail → pass |

Additional regression checks reject outside paths and symlink escapes, preserve
read-only requests, and prevent a file read from replacing explicitly requested
test execution. The final Ornith multi-file case made both patches and passed
tests within the same eight-iteration budget.

## Method and limits

The suite now contains 18 small Python-fixture tasks and exercises all ten
registered tools across the discovery runs. Cases run in separate processes
and disposable workspaces. Edits are checked with independent unit tests;
file snapshots detect modified tests and unexpected files. Execution is
restricted to exact fixture commands. Both models use temperature zero, an
output cap of 1,024 tokens, eight agent iterations, and twenty tool calls.
Model digests, quantization, and configuration are in
[environment.json](environment.json). The models are installed Qwen 7.6B Q4_K_M
and Ornith 9B Q4_K_M; embeddings use nomic-embed-text.

Task timing includes model calls and executed tools, but excludes fixture setup,
initial indexing, and process startup. Loading, network conditions, and server
load affect timings. Unit tests use controlled responses; live cases use the
actual Ollama server. Citation checks are limited checks, not a semantic proof
of correctness. These fixtures do not establish reliability on large projects,
ambiguous multi-turn requests, arbitrary shell commands, or external services.
OwA can call its registered tools; it does not gain another assistant's model
or external integrations through these changes.

During final verification the server became unreachable twice. HTTP requests
through the configured SOCKS proxy timed out or failed to connect, and Tailscale
pings eventually timed out too. The interrupted rounds were stopped and are
not counted as agent-behavior failures. An earlier harness-only false failure
(counting setup-created `.gitignore` as an agent edit) was corrected by taking
the file snapshot after fixture setup. That diagnostic run is excluded above.
The extra partial second discovery round is likewise excluded from the table.

## Finish the repeatability check

Once the server connection is stable, run the full matrix for each model
sequentially to avoid overlapping model loads:

```bash
export ALL_PROXY=socks5h://127.0.0.1:1055
.venv312/bin/python scripts/eval-agent.py --model qwen2.5-coder:7b --repeat 2 --output .owa/benchmark-qwen-final.json
.venv312/bin/python scripts/eval-agent.py --model ornith:9b --repeat 2 --output .owa/benchmark-ornith-final.json
```

The benchmark checks connectivity/model availability first, saves each completed
case, and reports the planned run count separately. Keep unsuccessful runs and
infrastructure interruptions visible when reporting the completed results.
