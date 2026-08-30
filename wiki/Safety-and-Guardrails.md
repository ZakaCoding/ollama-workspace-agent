# Safety and Guardrails

OwA is designed to be useful in real workspaces without pretending that a model-generated shell command is automatically safe. The guardrails are there to reduce accidental surprises, but they are not complete security guarantees.

## Workspace boundary

File operations resolve paths against the configured workspace root. Absolute paths and traversal attempts like `../` are rejected before a file is read or written.

The shell tool follows the same principle: it validates commands against the workspace and asks the user to confirm before execution. Unexpected or missing input is treated as denial rather than approval.

## Task isolation

A fresh `AgentState` is created for each request. This helps prevent stale task instructions or context from leaking between unrelated prompts.

## Prompt constraints

The system prompt tells the model the workspace root, allowed behavior, tool selection rules, iteration limits, and the requirement to verify changes before claiming completion. Prompt guidance is helpful but not a complete security boundary by itself.

## What is not guaranteed

- a local model can still make incorrect or destructive edits
- shell execution can still affect files inside the workspace
- the tool layer does not replace a complete organizational approval process
- Ollama calls are only as secure as the local environment running them
- any file read or indexed may expose secrets if those files are in scope
- the semantic index can contain stale data until it is rebuilt

## Safe use practices

- run the agent in a disposable or version-controlled repo
- keep `.env` and secrets outside the indexed workspace when possible
- review diffs and logs before accepting changes
- keep shell access restricted to trusted workflows
- treat model output as suggestions until verified
- avoid exposing shell or file tools to untrusted users without extra policy checks

## Security review checklist

When changing agent behavior, check that the project still handles:

- absolute path rejection
- traversal attempts
- symlink edge cases
- shell parsing and redirection
- confirmation denial and EOF behavior
- argument validation for all tools
- prompt iteration limits
- accidental secret exposure in indexed content
