# Tools

The model sees JSON schemas from `app/tools/registry.py` and receives tool results as text. Tool names are the public contract between the agent and the model.

## Current tools

| Tool | Purpose | Safety boundary |
| --- | --- | --- |
| `list_dir` | List files and directories. | Resolves paths inside the workspace. |
| `read_file` | Read a UTF-8 text file. | Rejects absolute paths and workspace escapes. |
| `patch_file` | Targeted search-and-replace edit on an existing file. | Resolves destination inside the workspace. Fails if `old_str` not found or matches multiple locations. |
| `write_file` | Create or fully replace a text file. | Resolves destination inside the workspace. |
| `search_code` | Search indexed source by semantic similarity. | Reads the local `.owa/index.db` only. |
| `code_review` | Review a Python file for common security risks. | Read-only. |
| `run_command` | Execute a shell command after user confirmation. | Rejects commands targeting paths outside the workspace. |
| `git_status` | Show branch and working-tree state. | Runs against the workspace repository. |
| `git_diff` | Show the current Git diff. | Runs against the workspace repository. |
| `git_log` | Show recent commits. | Runs against the workspace repository. |

## Tool preference

- Prefer `patch_file` over `write_file` when modifying an existing file — it makes a targeted change without replacing the whole file.
- `write_file` is for creating new files or fully replacing existing ones.
- `write_file` and `patch_file` are both blocked on read-only tasks (questions, explanations, inspections).

## Adding a tool

1. Implement a small callable in `app/tools/`.
2. Add a JSON schema to `TOOLS` in `app/tools/registry.py`.
3. Add the callable to `FUNCTIONS` under the exact same name.
4. Add focused tests for valid behavior and boundary cases.
5. Update this page and the changelog.

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
            "required": ["value"],
        },
    },
}
```

## Tool design guidance

- Return concise, useful text — the model consumes the result.
- Validate inputs at the tool boundary.
- Avoid hidden side effects.
- Keep filesystem operations workspace-aware.
- Make failures explicit rather than returning plausible-looking success text.
- Test malformed input, denied access, and unavailable dependencies.
