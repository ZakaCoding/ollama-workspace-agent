# Safety and Guardrails

This project is a local coding-agent prototype. Its guardrails reduce accidental scope violations, but they do not make arbitrary model-generated shell commands safe.

## Workspace boundary

Filesystem tools resolve user-provided paths against the configured workspace. Absolute paths and paths that escape with `..` are rejected.

The shell tool applies a similar boundary check to command paths and asks for confirmation before execution. End-of-file or unavailable input is treated as rejection rather than approval.

## Task isolation

A fresh `AgentState` is created for each user request. This prevents stale task data from silently carrying requirements between unrelated prompts.

## Prompt constraints

The system prompt tells the model the workspace root, available behavior, tool preferences, iteration limits, and the requirement to verify implementation details. Prompt instructions improve behavior but are not a security boundary by themselves.

## What is not guaranteed

- Shell commands can still have effects inside the workspace.
- A trusted local model can still make destructive or incorrect edits.
- The agent does not provide a complete approval policy for every file operation.
- Network calls to Ollama are not authenticated by this application.
- Secrets in files may be exposed to the model when explicitly read or indexed.
- The semantic index may retain stale source content until rebuilt or cleaned.

## Safe operating practice

- Run the agent in a disposable or version-controlled workspace.
- Keep `.env` private and avoid indexing secret-bearing files.
- Review proposed writes and Git diffs.
- Use a least-privilege account for the agent process.
- Do not expose the shell tool to untrusted users without an additional policy layer.
- Treat model output as untrusted suggestions until verified.

## Security review checklist

When changing the agent, test:

- absolute path rejection
- traversal rejection
- symlink behavior
- shell command parsing and redirection
- confirmation denial and EOF handling
- tool argument validation
- prompt and tool-call iteration limits
- accidental secret inclusion in index results
