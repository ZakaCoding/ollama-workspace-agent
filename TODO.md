# TODO

## Features

- [ ] **Multi-model support** — auto-route tasks to different models based on intent (e.g. `LLM_MODEL` for chat, `CODE_MODEL` for code tasks like write/fix/refactor)
- [ ] **`/status` show current model** — display active chat model alongside index chunk count
- [ ] **`@filename` context** — attach a specific file to a message so the agent reads it without needing to call `read_file`

## Known Limitations

- Emoji rendering broken with `ornith:9b` — model outputs mojibake, not an OwA bug
- `agent.stream()` does not handle tool calls (tool activity shown via stderr, final response streamed)
