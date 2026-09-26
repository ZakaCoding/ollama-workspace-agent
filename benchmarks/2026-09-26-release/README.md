# 0.7.0 release validation attempt

The candidate was checked on 2026-09-26 using the current 23-case live
evaluation suite. Live evaluation remains incomplete because the configured
remote Ollama service accepts catalog requests but does not return inference
responses within the bounded timeouts.

- `GET /v1/models` returned HTTP 200 in 0.52 seconds.
- `GET /api/ps` returned HTTP 200 with no loaded models.
- `qwen2.5-coder:7b`: the `command` case exceeded the evaluator's 240-second
  child timeout. The remaining cases were not run.
- Direct 16-token chat requests to `qwen2.5-coder:7b` and `ornith:9b` each
  exceeded a 45-second read timeout.

The full 46-run evaluation for each model must be rerun once inference is
responsive. These timeouts do not establish an agent correctness result.

Local release checks completed: 415 tests passed, the streaming check passed,
`pip check` found no broken requirements, release metadata was valid for
`v0.7.0`, and the wheel and source distribution built successfully.
