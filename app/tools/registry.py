from app.tools.basic import list_dir, read_file, run_command


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories inside the current workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path. Defaults to '.'",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative file path.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command inside the workspace. "
                "Use this for git, tests, package managers, build commands, "
                "and other development operations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]


FUNCTIONS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "run_command": run_command,
}