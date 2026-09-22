# OwA 0.7.0 workflow and grounding evaluation

The local implementation passes **354 tests on Python 3.12 and Python 3.14**.
The final frozen-source Qwen matrix passed **40/40** cases. Ornith completed
**all 40 planned case-runs in 42 attempts**, with two interrupted attempts
preserved and retried. Every one of the twenty cases passed twice on each model.
Ornith's runs were interrupted and resumed, not two uninterrupted matrices.

## Recorded matrices

| Model | Passed / attempted / planned | Grounding checks | Independent patch checks | Successful tools / calls | Median / maximum task time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen 7.6B Q4_K_M, final source | 40 / 40 / 40 | 10/10 | 10/10 | 61/64 | 3.05 / 9.36 s |
| Ornith 9B Q4_K_M, all attempts | 40 / 42 / 40 | 10/12 | 10/10 | 71/73 | 11.22 / 70.29 s |

Raw traces: [final Qwen matrix](qwen-final.json),
[initial Ornith segment](ornith-interrupted.json),
[first Ornith continuation](ornith-resume-interrupted.json),
[final Ornith continuation](ornith-resume-final.json), and
[machine-readable summary](summary.json). The earlier successful
[Qwen matrix](qwen-matrix.json) is retained but excluded from the table.
Qwen's three unsuccessful tool calls consist of two expected initial failing
tests and one patch whose source text did not match; it corrected the patch and
passed independent tests. Ornith's two unsuccessful tool calls are expected
initial test failures. Its two unsuccessful grounding assertions occurred during
interrupted model requests; both affected cases passed on retry.

For Ornith, the initial segment supplied twenty first-round successes and two
second-round successes. The first continuation supplied six further successes;
the final continuation supplied the remaining twelve. Raw continuation segments
retain their original local `run: 1` labels; they map to the unfinished logical
second round. The summary checks that every case has exactly two successful runs.

Ornith's failed retrieval attempt recorded two failed model requests, no token
usage, a fallback response, and `done` with `completed: false`. Heartbeats
continued throughout the wait. This is classified as infrastructure failure;
the groundedness assertion necessarily failed because no grounded answer was
produced. The first resume attempt failed preflight without running any cases.
A subsequent Tailscale ping and Ollama health request succeeded, allowing the
unfinished cases to be retried. The [first resumed run](ornith-resume-interrupted.json)
passed six cases, including the previously interrupted retrieval case, before
both requests failed in `long_history`. The evaluator now records exception
types and HTTP status/body diagnostics and treats rejected requests (400, 413,
422) as agent failures rather than infrastructure failures. The earlier traces
lack that detail, so their infrastructure classification is based only on all
model requests failing; it does not establish the underlying cause.

## What was evaluated

The suite now has twenty cases: the previous eighteen plus a large evidence
chunk whose requested symbol appears after the normal prefix limit, and a
question about an absent symbol that must be refused. Each case runs in its
own disposable workspace. The evaluator uses the service event stream,
independent source tests, file snapshots, and exact-command approval. It records
model requests, tool outcomes, grounding assertions, patch checks, event traces,
and task latency. Grounding assertions are fixture checks, not semantic proof.

The initial [exploratory smoke run](exploratory-smoke.json) passed compression
and editing. It incorrectly marked a correct absent-symbol refusal as failed
because the evaluator did not recognize “could not locate.” That predicate was
corrected before the full matrices. The trace is retained as evaluation history,
not counted as an agent regression.

[Environment metadata](environment.json) records model digests, budgets, Python,
the base commit, and final runtime source hashes. These runs used an uncommitted
worktree based on `929b81f`, temperature zero, 8,192 context-budget tokens, 1,024
output tokens, eight iterations, and twenty tool calls. The compression and
absent-symbol fixtures additionally cap evidence at 2,000 characters.
Timing excludes fixture setup, indexing, and process startup. Model loading,
server load, and network behavior were not controlled for comparison.

The final Qwen matrix used the frozen runtime and evaluator hashes in the
environment file. The initial Qwen matrix preceded final citation-allowlist
hardening and atomic HTTP completion capture. Ornith's initial segment overlapped
those review changes; its resumed cases used the final runtime, and server-error
diagnostics were added before the last continuation. All final changes have
automated coverage. Ornith should not be described as two uninterrupted,
frozen-source final matrices.

## Local validation

- Python 3.12: 354 tests pass; dependency consistency check passes.
- Python 3.14: 354 tests pass in a clean pinned environment. FastAPI/Starlette
  produce 343 deprecation warnings about an asyncio helper; no test failures.
- Python 3.11 and 3.13 are configured in CI but were not run locally.
- `scripts/check-stream.py` passes on both installed Python versions. It uses a
  real local HTTP connection and withholds the model stub's response until the
  client receives a tool-start event. Unicode and final completion are checked.
- The 0.7.0 wheel and source distribution build. The wheel installs and its CLI
  help runs outside the checkout. The source archive includes release scripts,
  test fixtures, pinned dependencies, and documentation. All 354 tests also pass
  from the extracted source archive on Python 3.14.
- Release metadata and `git diff --check` pass. No tag or package was published.

Sandboxed API tests stalled and were interrupted; complete suites ran outside
the sandbox. Live model access likewise required the existing Tailscale proxy
outside the sandbox. These execution limitations are separate from agent quality.

## Reproduction

```bash
export ALL_PROXY=socks5h://127.0.0.1:1055
.venv312/bin/python scripts/eval-agent.py --model qwen2.5-coder:7b --repeat 2 --output .owa/qwen.json
.venv312/bin/python scripts/eval-agent.py --model ornith:9b --repeat 2 --output .owa/ornith.json
.venv312/bin/python -m pytest -q
.venv312/bin/python scripts/check-stream.py
```

These small fixtures do not establish performance on large repositories,
arbitrary patches, or long multi-turn tasks. Resource profiles are starting
budgets, not measured hardware capacity claims.
