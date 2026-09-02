import json
import re
from importlib.metadata import version as pkg_version
from pathlib import Path

from rich.console import Console

from app.agent.state import AgentState
from app.agent.context import ContextBuilder
from app.agent.verifier import verify_evidence_citations, verify_tool_result
from app.indexer.search import search
from app.llm.client import LLMClient
from app.tools.registry import TOOLS, FUNCTIONS

console = Console(stderr=True)
NO_RESPONSE_MESSAGE = "I couldn't produce a response. Please try again."

WORKSPACE = Path.cwd().resolve()
HISTORY_PATH = WORKSPACE / ".owa" / "history.json"


RETRIEVAL_PREFIXES = (
    "according to ",
    "based on this repository",
    "based on the repository",
    "in this repository",
    "in the repository",
    "from this repository",
    "where ",
    "what ",
    "what's ",
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
    "last ",
    "latest ",
    "recent ",
    "is there ",
    "does ",
    "do ",
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


GIT_INTENT_PHRASES = (
    "last commit",
    "latest commit",
    "recent commit",
    "commit history",
    "recent changes",
    "what changed",
    "what is new",
    "what's new",
    "git status",
    "git diff",
    "release changes",
    "branch",
)


RESUME_INTENT_PHRASES = (
    "resume from git diff",
    "resume from the git diff",
    "continue from git diff",
    "continue previous work",
    "what was i working on",
)


COMMIT_MESSAGE_PHRASES = (
    "commit message",
    "commit messages",
)


CONVERSATIONAL_INPUTS = {
    "yes", "no", "ok", "okay", "sure", "thanks", "thank you",
    "yes please", "no thanks", "got it", "lol", "haha", "nice",
    "cool", "great", "good", "fine", "alright", "yep", "nope",
    "hi", "hello", "hey", "bye", "goodbye",
}


def task_is_conversational(task: str) -> bool:
    """Short ambiguous inputs that should never trigger the tool loop."""
    normalized = task.strip().lower().rstrip("!?.")
    if normalized in CONVERSATIONAL_INPUTS:
        return True
    # 3 words or fewer with no action words and no retrieval prefix
    words = normalized.split()
    if len(words) <= 3 and not any(w in normalized for w in EXPLICIT_ACTION_WORDS):
        return not normalized.startswith(RETRIEVAL_PREFIXES)
    return False


def _dedup_response(text: str) -> str:
    """Truncate model output that contains repeated sentences (loop detection)."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    seen: dict[str, int] = {}
    for i, s in enumerate(sentences):
        key = s.strip().lower()
        if not key:
            continue
        if key in seen:
            # Second occurrence — truncate here
            return " ".join(sentences[: seen[key] + 1]).strip()
        seen[key] = i
    return text


def task_is_read_only(task: str) -> bool:
    normalized = task.strip().lower()
    return not any(word in normalized for word in EXPLICIT_ACTION_WORDS)


def task_requires_git_tools(task: str) -> bool:
    normalized = " ".join(task.strip().lower().split())
    return (
        any(phrase in normalized for phrase in GIT_INTENT_PHRASES)
        or task_is_resume_request(task)
        or task_is_changelog_request(task)
        or task_is_commit_message_request(task)
    )


def task_is_resume_request(task: str) -> bool:
    normalized = " ".join(task.strip().lower().split())
    return any(phrase in normalized for phrase in RESUME_INTENT_PHRASES)


def task_is_changelog_request(task: str) -> bool:
    normalized = " ".join(task.strip().lower().split())
    return "changelog" in normalized or "change log" in normalized


def task_is_commit_message_request(task: str) -> bool:
    normalized = " ".join(task.strip().lower().split())
    return any(phrase in normalized for phrase in COMMIT_MESSAGE_PHRASES)


def task_requires_code_search(task: str) -> bool:
    normalized = task.strip().lower()
    if any(word in normalized for word in EXPLICIT_ACTION_WORDS):
        return False
    if normalized.startswith(RETRIEVAL_PREFIXES):
        return True
    return (
        "repository" in normalized
        and normalized.endswith("?")
    )


def _tools_for_task(
    git_task: bool,
    retrieval_task: bool,
    task: str = "",
):
    if not git_task:
        return [] if retrieval_task else TOOLS

    git_names = {"git_status", "git_diff", "git_log"}
    normalized = " ".join(task.strip().lower().split())
    changelog_task = task_is_changelog_request(task)
    resume_task = task_is_resume_request(task)
    commit_message_task = task_is_commit_message_request(task)
    if changelog_task:
        git_names.add("read_file")
        if any(word in normalized for word in ("update", "add", "edit", "change", "patch")):
            git_names.add("patch_file")
    elif resume_task:
        git_names.update({"read_file", "search_code"})
    elif commit_message_task:
        git_names.add("read_file")
    mixed_search = retrieval_task and any(
        marker in normalized
        for marker in (
            "implemented",
            "implementation",
            "how does",
            "where is",
            "which file",
            "architecture",
        )
    )
    if mixed_search:
        git_names.update({"search_code", "read_file"})
    return [
        tool for tool in TOOLS
        if tool["function"]["name"] in git_names
    ]


def _workflow_message(task: str) -> str:
    if task_is_changelog_request(task):
        return (
            "CHANGELOG WORKFLOW: inspect CHANGELOG.md and the relevant Git "
            "status/diff/log first. Only discuss or modify CHANGELOG.md. "
            "Do not create or modify Ollama configuration, files outside the "
            "workspace, or unrelated files. If the user asks only for a "
            "message or suggestion, do not patch anything."
        )
    if task_is_resume_request(task):
        return (
            "RESUME WORKFLOW: inspect Git status, diff, recent log, and only "
            "the relevant files. Conclude with current state, what changed, "
            "what remains, and the next verified step. Never claim a command "
            "ran unless its tool result shows it."
        )
    if task_is_commit_message_request(task):
        return (
            "COMMIT MESSAGE WORKFLOW: inspect Git status, diff, and recent log "
            "before drafting a message. Return a commit message only. Do not "
            "run git add, git commit, or any write command. A positive reply "
            "such as 'yes please' is not commit authorization."
        )
    return ""


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


def _repository_context_message(search_context: str) -> str:
    if search_context:
        return (
            "Relevant repository context retrieved by OwA.\n\n"
            "Answer only with claims directly supported by this context. "
            "If the context does not mention the requested subject, say that "
            "OwA could not verify it in this repository. Do not infer that a "
            "technology, file, or architecture exists from the user's wording. "
            "Do not explore the filesystem or use tools for this read-only "
            "repository question.\n\n"
            + search_context
        )

    return (
        "No relevant repository evidence was found for this question.\n\n"
        "This is a read-only repository question. Do not use tools or invent "
            "files, technologies, dependencies, or architecture. Reply in one "
            "short sentence saying that OwA could not verify the requested subject "
            "in this repository."
    )


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
            self._allowed_citations = set()
            return ""

        results = search(index_path, task, limit=10)
        self._allowed_citations = {
            f"{result.get('path', 'unknown')}#chunk={result.get('chunk_index', '?')}"
            for result in results
        }
        return self.context_builder.build(results)

    def _verify_answer(self, content: str, retrieval_task: bool) -> str:
        if not retrieval_task:
            return content

        verification = verify_evidence_citations(
            content,
            getattr(self, "_allowed_citations", set()),
            require_citation=bool(getattr(self, "_allowed_citations", set())),
        )
        if verification.passed:
            return content
        return (
            f"{content}\n\n"
            f"Client verification: {verification.message}"
        )

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
            if re.search(rf"\bI\s+{word}\b", content, re.IGNORECASE)
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
        self._allowed_citations = set()
        read_only_task = task_is_read_only(user_input)
        retrieval_task = task_requires_code_search(user_input)
        git_task = task_requires_git_tools(user_input)

        if retrieval_task and not git_task:
            search_context = self._build_search_context(user_input)
            self.messages.append(
                {
                    "role": "system",
                    "content": _repository_context_message(search_context),
                }
            )

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )
        workflow_message = _workflow_message(user_input)
        if workflow_message:
            self.messages.append(
                {"role": "system", "content": workflow_message}
            )

        while True:
            try:
                self.state.next_iteration()
            except RuntimeError as exc:
                self._save_history()
                return str(exc)
            self._trim_messages()

            available_tools = _tools_for_task(
                git_task,
                retrieval_task,
                user_input,
            )

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
                content = message.get("content") or ""
                content = _dedup_response(
                    self._verify_answer(
                        self._add_verification_note(content),
                        retrieval_task and not git_task,
                    )
                )

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
        self._allowed_citations = set()
        retrieval_task = task_requires_code_search(user_input)
        git_task = task_requires_git_tools(user_input)
        messages_snapshot = len(self.messages)

        if git_task:
            try:
                content = self.run(user_input) or NO_RESPONSE_MESSAGE
            except Exception:
                content = NO_RESPONSE_MESSAGE
            yield _dedup_response(content)
            return

        if retrieval_task:
            search_context = self._build_search_context(user_input)
            self.messages.append(
                {
                    "role": "system",
                    "content": _repository_context_message(search_context),
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
        except Exception:
            # Partial output cannot be shown safely because the fallback may
            # replace it with a complete non-streaming response.
            content_parts = []

        content = "".join(content_parts)

        if not content.strip():
            if task_is_conversational(user_input):
                # For conversational inputs, retry stream once — never enter tool loop
                try:
                    retry_parts = []
                    for chunk in self.llm.chat_stream(self.messages):
                        retry_parts.append(chunk)
                    content = "".join(retry_parts)
                except Exception:
                    content = ""
                if content:
                    yield content
                else:
                    yield NO_RESPONSE_MESSAGE
            else:
                # Non-conversational: restore messages and delegate to run() with tool loop
                self.messages = self.messages[:messages_snapshot]
                try:
                    content = self.run(user_input) or ""
                except Exception:
                    content = ""
                if content:
                    yield _dedup_response(content)
                else:
                    yield NO_RESPONSE_MESSAGE
            return

        content = _dedup_response(
            self._verify_answer(
                self._add_verification_note(content),
                retrieval_task,
            )
        )
        yield content

        self.messages.append(
            {
                "role": "assistant",
                "content": content,
            }
        )
        self.state.completed = True
        self._save_history()