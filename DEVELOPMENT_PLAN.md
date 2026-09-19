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
- [ ] Add startup status showing active budgets and model capabilities.
- [ ] Add latency and token-use measurements without sending telemetry.

### Phase 2 — Reliable small-model orchestration

- [x] Route conversational, retrieval, Git, and change tasks with minimal tool
  sets.
- [ ] Add a compact planning step for multi-file changes.
- [ ] Validate tool arguments before execution and recover from malformed calls.
- [ ] Keep one clear verification step after every write or command.

### Phase 3 — Efficient project grounding

- [ ] Keep incremental indexing fast and remove stale records reliably.
- [ ] Add model and embedding metadata to `.owa/index.db`.
- [ ] Improve hybrid retrieval for symbols, filenames, and exact phrases.
- [ ] Add context compression for large evidence sets.

### Phase 4 — Developer workflow

- [ ] Make API and CLI behavior share the same service lifecycle.
- [ ] Add reliable streamed tool progress for slow local models.
- [ ] Improve `/model`, `/status`, `/index`, and configuration diagnostics.
- [ ] Add reproducible CI coverage for supported Python versions.

### Phase 5 — Evaluation and release quality

- [ ] Maintain a fixed small-model evaluation set for coding tasks.
- [ ] Track groundedness, tool success, patch correctness, and latency.
- [ ] Document resource profiles for common local machines.
- [ ] Promote stable milestones through the changelog and release process.

## Current update

The first implementation slices are complete: context and output budgets are
configurable, bounded, documented, and covered by tests; cited claims are
checked against the retrieved chunk, retried with a stricter prompt, and
refused when the model continues to invent unsupported content. The next
engineering task is a compact planning and verification step for multi-file
changes, while preserving the focused tool sets selected here.
