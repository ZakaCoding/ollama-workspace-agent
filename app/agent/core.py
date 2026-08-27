import json
from pathlib import Path

from app.agent.state import AgentState
from app.agent.verifier import verify_tool_result
from app.llm.client import LLMClient
from app.tools.registry import TOOLS, FUNCTIONS


WORKSPACE = Path.cwd().resolve()


SYSTEM_PROMPT = f"""
You are a local software engineering agent.

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
- write_file -> create or replace files

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
"""


class Agent:

    def __init__(self):
        self.llm = LLMClient()
        self.state = None

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def run(self, user_input: str):
        self.state = AgentState(task=user_input)

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        while True:
            self.state.next_iteration()

            response = self.llm.chat(
                messages=self.messages,
                tools=TOOLS,
            )

            choice = response["choices"][0]
            message = choice["message"]

            tool_calls = message.get(
                "tool_calls",
                [],
            )

            if not tool_calls:
                content = message.get(
                    "content",
                    "",
                )

                self.messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                    }
                )

                self.state.completed = True
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

                print()
                print(
                    f"🔧 Tool: {name}"
                )
                print(
                    "   Args:",
                    json.dumps(
                        arguments,
                        ensure_ascii=False,
                    ),
                )

                tool = FUNCTIONS.get(name)

                if tool is None:
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

                print(
                    "   ✓ Result received"
                )