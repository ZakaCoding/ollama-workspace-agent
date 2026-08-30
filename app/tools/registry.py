from app.tools.filesystem import (
    list_dir,
    read_file,
    patch_file,
    write_file,
)

from app.tools.git import (
    git_status,
    git_diff,
    git_log,
)

from app.tools.search import search_code
from app.tools.code_review import review_file
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
            "name": "patch_file",
            "description": (
                "Replace an exact block of text in an existing file. "
                "Use this for targeted edits — adding, changing, or removing "
                "a function, block, or lines — without rewriting the whole file. "
                "Prefer this over write_file whenever the file already exists. "
                "old_str must match exactly one location in the file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_str": {
                        "type": "string",
                        "description": "Exact text to replace. Must be unique in the file.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "Text to insert in place of old_str. Empty string to delete.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create or completely replace a text file inside the "
                "workspace. Use ONLY when the user explicitly requests "
                "a file modification; never use for questions, inspection, "
                "or analysis."
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
                "Execute a shell command when no dedicated tool is available "
                "and execution is explicitly requested or necessary for an "
                "explicitly requested task. Do not use for ordinary code "
                "questions or filesystem operations."
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

    {
        "type": "function",
        "function": {
            "name": "code_review",
            "description": (
                "Review a Python file for common security risks. This tool "
                "is read-only and returns structured findings with line "
                "numbers. Use only for an explicitly requested code review."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative Python file path.",
                    },
                },
                "required": ["path"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search the project's indexed source code using semantic "
                "search. IMPORTANT: use this tool FIRST when the user asks "
                "where something is implemented, how a feature works, or "
                "which files contain relevant functionality. This tool "
                "searches the existing project index and does not modify "
                "files. Examples: 'Where is tool execution implemented?', "
                "'Where is authentication handled?', 'How does the agent "
                "execute commands?', 'Where is the database connection "
                "created?'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Natural language description "
                            "of the code you are looking for."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return.",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }
]


FUNCTIONS = {
    "list_dir": list_dir,
    "read_file": read_file,
    "patch_file": patch_file,
    "write_file": write_file,

    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,

    "run_command": run_command,

    "code_review": review_file,

    "search_code": search_code,
}