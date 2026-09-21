# OwA agent benchmark — 2026-09-21

Both installed models passed all 18 cases twice: **Qwen 36/36** and
**Ornith 36/36**. This completes the repeatability check left unfinished in the
[2026-09-20 report](../2026-09-20/README.md), without further implementation
changes. All **312 automated tests pass**.

## Results

| Model | Passed / planned | Median task time | Total task time | Tool calls | Model requests | Raw traces |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Qwen 7.6B Q4_K_M | 36/36 | 3.26 s | 149.36 s | 64 | 108 | [qwen-final.json](qwen-final.json) |
| Ornith 9B Q4_K_M | 36/36 | 11.71 s | 565.78 s | 72 | 96 | [ornith-final.json](ornith-final.json) |

Every case passed in each round, including combined Git/edit requests,
test-before-edit recovery, multi-file editing, and read-only constraints.
Neither completed matrix reported an infrastructure failure. Ornith's second
security-review case took **170.47 seconds**, versus **11.51 seconds** in the
first round; it still passed within the 240-second timeout. The trace does not
establish the cause of that delay. Medians alone hide this latency variation.

## Environment and method

The evaluated checkout was `2a5a813bb9adf44c7bf16bd6463b9da803eaddab`, whose
latest implementation change is `a339b78`. Python was 3.12.3. Installed model
digests match the previous report; current metadata and budgets are recorded in
[environment.json](environment.json).

Qwen's full matrix ran first, followed by Ornith's full matrix, through the
Tailscale SOCKS proxy. Each model ran two rounds of the same 18 disposable
Python-fixture tasks. Settings remained temperature zero, 1,024 output tokens,
8,192 context-budget tokens, eight iterations, and twenty tool calls. Source
edits were checked by independent tests and file snapshots; only exact fixture
commands were automatically approved. Timing excludes fixture setup, initial
indexing, and process startup.

```bash
export ALL_PROXY=socks5h://127.0.0.1:1055
.venv312/bin/python scripts/eval-agent.py --model qwen2.5-coder:7b --repeat 2 --output .owa/benchmark-qwen-final.json
.venv312/bin/python scripts/eval-agent.py --model ornith:9b --repeat 2 --output .owa/benchmark-ornith-final.json
.venv312/bin/python -m pytest -q
```

The initial sandboxed benchmark attempt failed preflight before running any
cases. The sandboxed automated suite stalled at the first API test and was
interrupted. With execution outside the sandbox, both live matrices completed
and the automated suite passed in 4.30 seconds. These sandbox attempts are not
included in the matrix counts.

## Limits and next work

Two successful rounds establish observed repeatability for these small
fixtures, not general reliability on large projects or ambiguous multi-turn
tasks. Qwen was faster in this sequential run, but model loading, server load,
and network conditions were not controlled for a performance comparison.
Citation checks remain limited checks rather than semantic proof.

The next planned grounding task is improved hybrid retrieval for symbols,
filenames, and exact phrases. Larger real-project and multi-turn evaluations
remain future work.
