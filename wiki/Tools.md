# Tools

OwA exposes a small, carefully defined tool set to the model. The idea is not to give the agent unlimited freedom, but to make workspace operations predictable, reviewable, and bounded.

## Current tool set

| Tool | Purpose | Safety boundary |
| --- | --- | --- |
| `list_dir` | List files and directories in the workspace | rejects paths that escape the repo |
| `read_file` | Read a UTF-8 text file | disallows absolute or out-of-scope paths |
| `write_file` | Create or replace a file | resolves destination inside the workspace |
| `patch_file` | Make targeted in-place edits | only touches files in scope |
| `search_code` | Find relevant code via the local semantic index | reads only the local project index |
| `run_command` | Execute shell commands after confirmation | blocks unsafe or out-of-workspace actions |
| `git_status` | Inspect branch and working-tree state | scoped to the current repo |
| `git_diff` | Show file differences | repo-scoped and read-only |
| `git_log` | Show recent commit history | repo-scoped and read-only |
| `code_review` | Review Python code for common issues | limited to analysis of project files |

The calculator example is included as a small domain helper and is not treated as a core workspace tool in the public model contract.

## Why tool design matters

A coding agent is often only as reliable as the tools it can call. OwA keeps tool behavior explicit and narrow so the model must reason in a clear way rather than improvising broad access.

This matters for:

- workspace isolation
- predictable patching
- safe command approval
- easier debugging of bad model behavior
- transparent user review before actions happen

## Adding a new tool

1. Add the Python function in `app/tools/`.
2. Add the JSON schema to `TOOLS` in `app/tools/registry.py`.
3. Register the callable in `FUNCTIONS` under the same name.
4. Add tests for successful and failure cases.
5. Update docs if the tool becomes part of the public workflow.

Example schema shape:

```python
{
    "type": "function",
    "function": {
        "name": "example_tool",
        "description": "A precise description of the operation.",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {"type": "string"}
            },
            "required": ["value"]
        }
    }
}
```

## Design guidance

- keep outputs concise and useful for the model
- validate arguments before execution
- avoid hidden side effects
- make errors explicit instead of returning vague success text
- keep all file operations workspace-aware
- test malformed inputs, rejected paths, and unavailable services
