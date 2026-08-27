# Tools

The model sees JSON schemas from `app/tools/registry.py` and receives tool results as text. Tool names are the public contract between the agent and the model.

## Current tools

| Tool | Purpose | Safety boundary |
| --- | --- | --- |
| `list_dir` | List files and directories. | Resolves paths inside the workspace. |
| `read_file` | Read a UTF-8 text file. | Rejects absolute paths and workspace escapes. |
| `write_file` | Create or replace a text file. | Resolves the destination inside the workspace. |
| `git_status` | Show branch and working-tree state. | Runs against the workspace repository. |
| `git_diff` | Show the current Git diff. | Runs against the workspace repository. |
| `git_log` | Show recent commits. | Runs against the workspace repository. |
| `run_command` | Execute a shell command after confirmation. | Rejects commands targeting paths outside the workspace. |
| `search_code` | Search indexed source by semantic similarity. | Reads the local `.ai/index.db` only. |

The calculator module currently provides `add`, `subtract`, `multiply`, `divide`, and `power` as ordinary Python functions. It is a domain example and is not currently registered as a separate model tool.

## Adding a tool

1. Implement a small callable in `app/tools/`.
2. Add a JSON schema to `TOOLS`.
3. Add the callable to `FUNCTIONS` under the exact same name.
4. Add focused tests for valid behavior and boundary cases.
5. Update this page and the changelog if the tool becomes part of the public contract.

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

- Return concise, useful text because the model consumes the result.
- Validate inputs at the tool boundary.
- Avoid hidden side effects.
- Keep filesystem operations workspace-aware.
- Make failures explicit rather than returning plausible-looking success text.
- Test malformed input, denied access, and unavailable dependencies.
