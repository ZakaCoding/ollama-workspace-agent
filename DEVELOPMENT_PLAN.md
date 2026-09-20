# OwA Development Plan

OwA's goal is to be a capable local coding agent that works well with small
models and limited CPU, memory, and network resources. The system should gain
capability from grounding, orchestration, and verification rather than only
from using a larger model.

## Product principles

- Local first: Ollama remains the model boundary and project data stays local.
- Small model friendly: prompts, tools, context, and outputs must have explicit
  budgets.
- Evidence first: repository answers must come from indexed or directly read
  files and verified Git output.
- Safe by default: workspace boundaries and write confirmation remain enforced.
- Measurable progress: every feature needs focused tests and evaluation cases.

## Development phases

### Phase 1 — Resource-aware runtime

- [x] Make repository context size configurable with `OWA_CONTEXT_TOKENS`.
- [x] Make model response size configurable with `OWA_MAX_OUTPUT_TOKENS`.
- [x] Add bounds and tests for invalid and excessive settings.
- [x] Reject citation laundering when a cited chunk does not support the claim.
- [x] Add startup status showing active budgets and model capabilities.
- [x] Add latency and token-use measurements without sending telemetry.

### Phase 2 — Reliable small-model orchestration

- [x] Route conversational, retrieval, Git, and change tasks with minimal tool
  sets.
- [x] Add a compact planning step for multi-file changes.
- [x] Validate tool arguments before execution and recover from malformed calls.
- [x] Keep one clear verification step after every write or command.

### Phase 3 — Efficient project grounding

- [x] Keep incremental indexing fast and remove stale records reliably.
- [x] Add model and embedding metadata to `.owa/index.db`.
- [ ] Improve hybrid retrieval for symbols, filenames, and exact phrases.
- [ ] Add context compression for large evidence sets.

### Phase 4 — Developer workflow

- [ ] Make API and CLI behavior share the same service lifecycle.
- [ ] Add reliable streamed tool progress for slow local models.
- [ ] Improve `/model`, `/status`, `/index`, and configuration diagnostics.
- [ ] Add reproducible CI coverage for supported Python versions.

### Phase 5 — Evaluation and release quality

- [x] Maintain a fixed small-model evaluation set for coding tasks.
- [ ] Track groundedness, tool success, patch correctness, and latency.
- [ ] Document resource profiles for common local machines.
- [ ] Promote stable milestones through the changelog and release process.

## Current update

The first implementation slices are complete: context and output budgets are
configurable, bounded, documented, and covered by tests; cited claims are
checked against the retrieved chunk, retried with a stricter prompt, and
refused when the model continues to invent unsupported content. Multi-file
changes now receive a bounded plan before tool execution and require a
read-only check or relevant test after writes and commands. Tool arguments are
validated against the current tool schemas before execution, with correction
feedback for malformed arguments and retries bounded by the existing runtime
budgets. Focused tool sets and workspace boundaries remain enforced. Startup
and `/status` now show active context/output budgets, the evidence character
cap, and available Ollama model capabilities and maximum context metadata.
API clients display the server's settings, and unavailable metadata is shown
as unknown. Model request latency, failures, and reported token use are now
measured in memory and exposed through status without telemetry. Missing usage
is identified explicitly; retries and interrupted streams are counted as
separate attempts. Indexes now record embedding provenance and dimensions,
rebuild when configuration changes, and fall back to lexical search when
vectors are incompatible. Updates preserve the prior database on failure,
remove stale chunks, and reuse existing full-text records. Forced rebuilds and
compatibility diagnostics are available in the CLI and API. The next grounding
task is improved hybrid retrieval for symbols, filenames, and exact phrases.

Direct small-model testing also exposed and fixed request-instruction loss,
streaming tasks bypassing the tool loop, history contamination, and tool-call
format mismatches. The live evaluation script now checks greetings, file reads,
cited retrieval, and a real edit/test cycle in disposable projects. Both the
installed Qwen 7.6B and Ornith 9B models passed these four smoke tests; larger
coding tasks still require broader evaluation.

Project orientation now reads bounded excerpts from current files without an
index or embeddings. Discovery prunes dependencies, ignored directories, and
symlinks. Legacy indexes without FTS remain readable through lexical fallback.
Text-only tool calls now have a continuation/finish protocol, repeated failures
stop explicitly, and failed test commands require successful command verification.
The live evaluation set now contains 18 cases covering every registered tool,
informal requests, combined Git/edit tasks, read-only constraints, and actual
patch/test behavior. Repeated and subset runs save incremental traces and
report pass rates, latency, tool calls, and model requests. Infrastructure
failures are separated from agent failures. Live Qwen testing exposed routing
gaps in direct inspection, plain commands, informal edits, and combined Git/edit
requests; these now have focused regression coverage. Larger real-project and
multi-turn benchmarks remain future work.
The 2026-09-20 live benchmark reproduced and fixed seven distinct routing,
ordering, and path-handling failures. All 312 automated tests pass. Ornith passed
the first ten cases after the final fixes, including both previously failing
cases, before the server connection dropped again. Full repeated verification
for both models remains pending; raw results and limitations are recorded in
`benchmarks/2026-09-20/README.md`.
