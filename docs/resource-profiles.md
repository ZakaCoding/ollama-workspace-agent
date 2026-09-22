# Resource profiles

These are starting settings for OwA's prompt budgets, not measured hardware
capacity requirements. Model weights, quantization, Ollama context allocation,
other applications, and CPU/GPU placement determine whether a model fits.
No hardware purchase is implied by these examples.

| Existing machine / workload | Context budget | Output limit | Suggested approach |
| --- | ---: | ---: | --- |
| Memory-constrained laptop, CPU only | 4096 | 512 | Use an already-installed model that fits; inspect one file or make one small edit at a time. |
| General development machine | 8192 | 1024 | Start with the benchmark budgets; index incrementally and verify edits with focused tests. |
| Larger memory machine, multi-file work | 16384 | 2048 | Increase only if evidence is being omitted or responses truncate; compare task latency before keeping the change. |

For the first profile:

```dotenv
OWA_CONTEXT_TOKENS=4096
OWA_MAX_OUTPUT_TOKENS=512
```

At these three context settings, the current evidence character caps are 2,000,
11,472, and 44,240. Retrieval still selects at most five chunks, at most two per
file, and at most 3,000 source characters per chunk. Larger context settings
therefore do not guarantee more retrieved evidence. Long chunks use extractive
compression; omitted text is marked and may require reading the original file.
The character-to-token conversion is approximate, especially for non-English
text and dense code.

`OWA_CONTEXT_TOKENS` controls OwA evidence selection, not Ollama's allocated
context. `OWA_MAX_OUTPUT_TOKENS` limits each response, not the total work across
multiple requests. `/status` shows actual selected budgets, available model
metadata, and local request timing/token counters. Missing usage remains unknown.

The committed benchmark reports measure disposable coding tasks on the specific
server described in their environment files. They do not establish performance
on these laptop/desktop profiles. Re-run `scripts/eval-agent.py` on your own
installation before treating a preset as suitable. No model downloads are
performed by the evaluator.
