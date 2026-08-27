import json

from app.llm.client import LLMClient
from app.tools.registry import TOOLS, FUNCTIONS


SYSTEM_PROMPT = """
You are a local software engineering agent.

You operate inside the user's workspace.

CRITICAL RULES:
- When the user asks you to inspect the workspace, files, directories, code,
    or project structure, you MUST use the filesystem tools.
- Never answer a workspace inspection request from assumptions or conversation
    context.
- When the user asks you to execute a command, use run_command.
- Never invent file contents.
- Never claim a tool was used unless it was actually called.
- After receiving tool results, continue reasoning about the task.
- Verify results whenever possible.

Available tools:
- list_dir: inspect directories
- read_file: inspect files
- run_command: execute development commands

You are an agent, not merely a chatbot.
"""


class Agent:

    def __init__(self):
        self.llm = LLMClient()

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            }
        ]

    def run(self, user_input: str):

        self.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        while True:

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

            # --------------------------------------------------
            # Normal assistant response
            # --------------------------------------------------

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

                return content

            # --------------------------------------------------
            # Assistant requested tools
            # --------------------------------------------------

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

            # --------------------------------------------------
            # Execute every requested tool
            # --------------------------------------------------

            for tool_call in tool_calls:

                function = tool_call["function"]

                name = function["name"]

                arguments = function.get(
                    "arguments",
                    {},
                )

                if isinstance(arguments, str):

                    try:
                        arguments = json.loads(
                            arguments
                        )

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

                    result = (
                        f"Unknown tool: {name}"
                    )

                else:

                    try:

                        result = tool(
                            **arguments
                        )

                    except Exception as exc:

                        result = (
                            f"Tool execution error: "
                            f"{type(exc).__name__}: {exc}"
                        )

                print(
                    "   ✓ Result received"
                )

                # ----------------------------------------------
                # Send result back using the same tool call ID
                # ----------------------------------------------

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result,
                    }
                )