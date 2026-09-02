import json
import re
from importlib.metadata import version as pkg_version
from pathlib import Path

from rich.console import Console

from app.agent.state import AgentState
from app.agent.context import ContextBuilder
from app.agent.verifier import verify_tool_result
from app.indexer.search import search
from app.llm.client import LLMClient
from app.tools.registry import TOOLS, FUNCTIONS

console = Console(stderr=True)

WORKSPACE = Path.cwd().resolve()
HISTORY_PATH = WORKSPACE / ".owa" / "history.json"


RETRIEVAL_PREFIXES = (
    "where ",
    "what ",
    "how ",
    "which ",
    "why ",
    "explain ",
    "describe ",
    "find ",
    "list ",
    "show ",
    "search ",
    "look ",
    "tell me ",
    "can you explain ",
    "can you describe ",
    "summarize ",
    "trace ",
    "walk me ",
)


EXPLICIT_ACTION_WORDS = (
    "add ",
    "change ",
    "create ",
    "delete ",
    "fix ",
    "implement ",
    "modify ",
    "remove ",
    "update ",
    "write ",
    "refactor ",
    "rename ",
    "move ",
    "patch ",
    "run ",
)


def task_is_read_only(task: str) -> bool:
    normalized = task.strip().lower()
    return not any(word in normalized for word in EXPLICIT_ACTION_WORDS)


def task_requires_code_search(task: str) -> bool:
    normalized = task.strip().lower()
    if any(word in normalized for word in EXPLICIT_ACTION_WORDS):
        return False
    return normalized.startswith(RETRIEVAL_PREFIXES)


OWA_VERSION = pkg_version("ollama-workspace-agent")

SYSTEM_PROMPT = f"""
You are OwA (Ollama Workspace Agent) version {OWA_VERSION} —
an open-source local coding assistant.

You operate inside this workspace:

WORKSPACE ROOT:
{WORKSPACE}

IMPORTANT:
- All filesystem paths are relative to this workspace.
- Never assume another workspace such as /testbed, /workspace, or /app.
- Use the filesystem tools to discover the actual project.
- If a tests/ directory exists, use it; otherwise create a conventional tests/ directory.
- Verify work with the smallest relevant test or command before claiming success.
- Never claim completion without checking the required behavior.

You are an agent, not merely a chatbot.

==================================================
TOOL RULES
==================================================

Use tools whenever real workspace information is required.

FILESYSTEM:
- list_dir -> inspect directories
- read_file -> inspect files
- patch_file -> targeted edit on an existing file (preferred for modifications)
- write_file -> create a new file or fully replace an existing one

GIT:
- git_status -> inspect Git status
- git_diff -> inspect changes
- git_log -> inspect history

SHELL:
- run_command -> execute commands when no dedicated tool exists

IMPORTANT:

1. Use the most specific tool available.
2. Do NOT use run_command for filesystem operations.
3. Do NOT use run_command for Git status, diff, or log.
4. Do NOT duplicate an operation unnecessarily.
5. Never use cat, echo, printf, ls, grep, sed, tail, head, find, or heredocs to read or write files.
6. Use read_file/write_file instead.
7. Shell is allowed for tests, builds, Python execution, and other non-filesystem tasks.
8. After modifying a file, verify it when appropriate.
9. Never invent file contents or command output.
10. Never claim an action occurred unless a tool actually performed it.
11. Inspect before modifying when necessary.
12. When creating tests, inspect the project structure first and follow existing conventions.
13. A task is only complete once the required checks have passed.

==================================================
AGENT BEHAVIOR
==================================================

For complex tasks:

1. Understand the objective.
2. Inspect relevant files.
3. Decide what needs to change.
4. Make the smallest appropriate change.
5. Verify the change.
6. Run tests when appropriate.
7. Inspect failures.
8. Fix problems.
9. Verify again.
10. Report final results with evidence.

Avoid unnecessary tool calls.

Prefer direct, precise actions over exploratory noise.

Do not exceed {20} iterations or {50} tool calls per task.

CODE SEARCH:

CODEBASE SEARCH POLICY:

For code and project questions, the client retrieves relevant repository
context before calling the model:

1. Answer from the retrieved context when it contains the relevant evidence.
2. Do NOT wander through the filesystem for ordinary code questions.
3. Do NOT modify files unless the user explicitly requests a modification.
4. Do NOT run commands unless the user explicitly requests execution or
    command execution is necessary to complete an explicitly requested task.
5. For questions that only require understanding code, prefer:
        semantic search -> context builder -> answer

READ-ONLY TASK RULE:

If the user asks a question, explanation, inspection, search, debugging
analysis, or codebase understanding task:

- DO NOT write files or modify files.
- DO NOT run destructive commands.
- DO NOT create tests unless explicitly requested.
- DO NOT fix anything unless explicitly requested.
- Use only read-only tools unless the user explicitly asks for changes.

Treat an explicit request to modify files as the boundary that permits
write tools. Do not infer permission to edit from a question or from a
discovered issue.
"""


class Agent:

    def __init__(self):
        self.llm = LLMClient()
        self.context_builder = ContextBuilder()
        self.state = None
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._load_history()

    def _load_history(self):
        if HISTORY_PATH.exists():
            try:
                saved = json.loads(HISTORY_PATH.read_text())
                self.messages += [m for m in saved if m["role"] != "system"]
            except Exception:
                pass

    def _save_history(self):
        try:
            HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            non_system = [m for m in self.messages if m["role"] != "system"]
            HISTORY_PATH.write_text(json.dumps(non_system))
        except Exception:
            pass

    def clear(self):
        self.state = None
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        try:
            HISTORY_PATH.unlink(missing_ok=True)
        except Exception:
            pass

    def _trim_messages(self, max_pairs: int = 20):
        system = [m for m in self.messages if m["role"] == "system"]
        non_system = [m for m in self.messages if m["role"] != "system"]
        if len(non_system) > max_pairs * 2:
            non_system = non_system[-(max_pairs * 2):]
        self.messages = system + non_system

    def _allowed_tool_names(
        self,
        available_tools,
    ) -> set[str]:
        if not available_tools:
            return set()

        return {
            tool["function"]["name"]
            for tool in available_tools
        }

    def _validate_tool_calls(
        self,
        tool_calls,
        available_tools,
    ):
        allowed = self._allowed_tool_names(available_tools)
        valid = []
        invalid = []

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]

            if name in allowed:
                valid.append(tool_call)
            else:
                invalid.append(tool_call)

        return valid, invalid

    def _build_search_context(self, task: str) -> str:
        index_path = WORKSPACE / ".owa" / "index.db"

        if not index_path.exists():
            return ""

        results = search(index_path, task, limit=10)
        return self.context_builder.build(results)

    def _add_verification_note(self, content: str) -> str:
        changed_files = bool(
            self.state
            and self.state.files_changed
        )
        commands_run = bool(
            self.state
            and getattr(self.state, "commands_run", [])
        )
        claims = {
            "created": changed_files,
            "updated": changed_files,
            "modified": changed_files,
            "wrote": changed_files,
            "test": commands_run,
        }
        unsupported = [
            word
            for word, has_evidence in claims.items()
            if re.search(rf"\b{word}\b", content, re.IGNORECASE)
            and not has_evidence
        ]

        if not unsupported:
            return content

        return (
            f"{content}\n\n"
            "Client verification: no matching tool execution was recorded "
            "for this response, so these claims are not verified."
        )

    def run(self, user_input: str):
        self.state = AgentState(task=user_input)
        read_only_task = task_is_read_only(user_input)
        retrieval_task = task_requires_code_search(user_input)

        if retrieval_task:
            search_context = self._build_search_context(user_input)
            if search_context:
                self.messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Relevant repository context retrieved by OwA.\n\n"
                            "Use this context to answer the user's question. "
                            "Do not explore the filesystem unless the supplied "
                            "context is insufficient.\n\n"
                            + search_context
                        ),
                    }
                )

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        while True:
            self.state.next_iteration()
            self._trim_messages()

            available_tools = [] if retrieval_task else TOOLS

            response = self.llm.chat(
                messages=self.messages,
                tools=available_tools,
            )

            choice = response["choices"][0]
            message = choice["message"]

            tool_calls = message.get(
                "tool_calls",
                [],
            )

            valid_tool_calls, invalid_tool_calls = (
                self._validate_tool_calls(
                    tool_calls,
                    available_tools,
                )
            )

            if invalid_tool_calls:
                allowed_tool_names = self._allowed_tool_names(
                    available_tools
                )

                for tool_call in invalid_tool_calls:
                    tool_name = tool_call["function"]["name"]

                    console.print(f"[bold yellow]⚠ blocked tool:[/bold yellow] [dim]{tool_name}[/dim]")

                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": message.get("content", ""),
                            "tool_calls": [tool_call],
                        }
                    )

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": (
                                f"Tool '{tool_name}' is not available "
                                "for this step. You must use only the "
                                "currently available tools."
                            ),
                        }
                    )

                tool_calls = valid_tool_calls

                if not tool_calls:
                    continue

            if not tool_calls:
                content = message.get(
                    "content",
                    "",
                )
                content = self._add_verification_note(content)

                self.messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )

                self.state.completed = True
                self._save_history()
                return content

            assistant_message = {
                "role": "assistant",
                "content": message.get(
                    "content",
                    "",
                ),
                "tool_calls": tool_calls,
            }

            self.messages.append(
                assistant_message
            )

            for tool_call in tool_calls:
                self.state.record_tool_call()
                function = tool_call["function"]
                name = function["name"]
                arguments = function.get(
                    "arguments",
                    {},
                )

                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError as exc:
                        result = (
                            "Invalid tool arguments: "
                            f"{exc}"
                        )
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result,
                            }
                        )
                        self.state.record_error(result)
                        continue

                console.print(f"[dim]  ⚙ {name}({json.dumps(arguments, ensure_ascii=False)})[/dim]")

                tool = FUNCTIONS.get(name)

                if read_only_task and name in {
                    "write_file",
                    "patch_file",
                    "run_command",
                }:
                    result = (
                        f"Tool blocked: {name} is not allowed for a "
                        "read-only task."
                    )
                elif tool is None:
                    result = f"Unknown tool: {name}"
                else:
                    try:
                        result = tool(**arguments)
                    except Exception as exc:
                        result = (
                            f"Tool execution error: "
                            f"{type(exc).__name__}: {exc}"
                        )

                verification = verify_tool_result(name, result)
                if not verification.passed:
                    self.state.record_error(verification.message)

                self.state.update_from_tool_result(
                    tool_name=name,
                    arguments=arguments,
                    result=result,
                )

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )

                console.print(f"[dim]    ✓ done[/dim]")

    def stream(self, user_input: str):
        self.state = AgentState(task=user_input)
        retrieval_task = task_requires_code_search(user_input)
        messages_snapshot = len(self.messages)

        if retrieval_task:
            search_context = self._build_search_context(user_input)
            if search_context:
                self.messages.append(
                    {
                        "role": "system",
                        "content": (
                            "Relevant repository context retrieved by OwA.\n\n"
                            "Use this context to answer the user's question. "
                            "Do not explore the filesystem unless the supplied "
                            "context is insufficient.\n\n"
                            + search_context
                        ),
                    }
                )

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        content_parts = []
        self._trim_messages()
        try:
            for content in self.llm.chat_stream(self.messages):
                content_parts.append(content)
                yield content
        except Exception:
            pass

        content = "".join(content_parts)

        if not content.strip():
            # Stream yielded nothing — restore messages and delegate to run()
            # which has the full tool loop
            self.messages = self.messages[:messages_snapshot]
            try:
                content = self.run(user_input) or ""
            except Exception:
                content = ""
            if content:
                yield content
            return

        self.messages.append(
            {
                "role": "assistant",
                "content": self._add_verification_note(content),
            }
        )
        self.state.completed = True
        self._save_history()