from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:

    task: str

    messages: list[dict[str, Any]] = field(
        default_factory=list
    )

    tool_calls: int = 0

    iteration: int = 0

    max_iterations: int = 20

    max_tool_calls: int = 50

    files_changed: list[str] = field(
        default_factory=list
    )

    commands_run: list[str] = field(
        default_factory=list
    )

    errors: list[str] = field(
        default_factory=list
    )

    completed: bool = False

    def record_file_change(self, path: str):
        if path not in self.files_changed:
            self.files_changed.append(path)

    def record_command(self, command: str):
        self.commands_run.append(command)

    def record_error(self, error: str):
        self.errors.append(error)

    def record_tool_call(self):
        self.tool_calls += 1

        if self.tool_calls > self.max_tool_calls:
            raise RuntimeError(
                "Agent exceeded the maximum tool call budget."
            )

    def next_iteration(self):
        self.iteration += 1

        if self.iteration > self.max_iterations:
            raise RuntimeError(
                "Agent reached maximum iterations."
            )

    def update_from_tool_result(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        result: str,
    ):
        """
        Update state after a tool has executed.
        """

        if tool_name in {"write_file", "patch_file"}:
            path = arguments.get("path")

            if path:
                self.record_file_change(path)

        elif tool_name == "run_command":
            command = arguments.get("command")

            if command:
                self.record_command(command)

        if result is None:
            self.record_error(
                f"{tool_name}: no result returned"
            )
