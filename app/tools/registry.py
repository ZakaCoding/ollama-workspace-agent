from app.tools.filesystem import (
    list_dir,
    read_file,
    write_file,
)

from app.tools.git import (
    git_status,
    git_diff,
    git_log,
)

from app.tools.shell import (
    run_command,
)


TOOLS = [

    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": (
                "List files and directories inside the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path.",
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
            "description": (
                "Read a text file inside the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    }
                },
                "required": ["path"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or completely replace a text file "
                "inside the workspace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": [
                    "path",
                    "content",
                ],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": (
                "Show the current Git branch and working tree status."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": (
                "Show the current Git diff."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "git_log",
            "description": (
                "Show recent Git commits."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Execute a shell command when no dedicated "
                "tool is available. Use this for tests, builds, "
                "package managers, Docker, PHP, Python, Node, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                    },
                },
                "required": ["command"],
            },
        },
    },
]


FUNCTIONS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "write_file": write_file,

    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,

    "run_command": run_command,
}