# Getting Started

## Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com) running on a reachable machine
- A chat model installed in Ollama, such as `llama3.1:8b` or `qwen2.5-coder`
- An embedding model installed in Ollama, such as `nomic-embed-text`

## Install

The recommended install is via pipx for an isolated environment:

```bash
pipx install ollama-workspace-agent
```

Or with pip:

```bash
pip install ollama-workspace-agent
```

## Configure

Run OwA once and type `/setup` — it walks you through the configuration interactively and saves to `~/.config/owa/.env`.

Or create the config manually:

```env
# ~/.config/owa/.env
LLM_BASE_URL=http://YOUR_OLLAMA_HOST:11434/v1
LLM_MODEL=llama3.1:8b
EMBEDDING_BASE_URL=http://YOUR_OLLAMA_HOST:11434
EMBEDDING_MODEL=nomic-embed-text
```

You can also place a `.env` in your project root to override the global config for that project.

## Verify Ollama

```bash
curl http://YOUR_OLLAMA_HOST:11434/api/tags
```

Pull the models you need:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

## Run

```bash
cd your-project
owa
```

OwA auto-indexes your project on first run and saves the index to `.owa/`. Once ready, start chatting.

## CLI Commands

| Command   | Description                        |
|-----------|------------------------------------|
| `/setup`  | Configure Ollama connection        |
| `/model`  | Switch the active chat model       |
| `/index`  | Rebuild the project index          |
| `/status` | Show index status                  |
| `/clear`  | Clear conversation history         |
| `/help`   | Show available commands            |
| `/quit`   | Exit                               |

## Indexing

OwA auto-indexes on first run. Common directories are excluded automatically (`node_modules`, `dist`, `build`, `.github`, `.git`, `.venv`, `vendor`, `target`, etc.).

To exclude additional files or directories, create a `.owaignore` in your project root:

```
# .owaignore
secrets.json
fixtures/
*.min.js
```

The local index is stored in `.owa/` and is automatically added to your `.gitignore` on first index.

## Session memory

Conversation history is saved to `.owa/history.json` and restored on next startup. Use `/clear` to wipe it.

## Common problems

- **`owa: command not found`** — make sure pipx's bin directory is on your PATH (`pipx ensurepath`), or activate your venv.
- **Embedding connection failure** — verify `EMBEDDING_BASE_URL` and that Ollama is running. The first call may be slow while the model cold-loads.
- **No search results** — run `/index` to build or rebuild the index.
- **`/setup` shows your existing host** — expected behavior, it reads your saved config as the default value.
- **Model goes off-topic in long sessions** — use `/clear` to reset context, or it trims automatically after 20 message pairs.
