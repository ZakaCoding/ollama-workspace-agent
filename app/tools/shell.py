import re
import subprocess

from rich.console import Console
from rich.prompt import Confirm

from app.tools.filesystem import WORKSPACE

console = Console(stderr=True)


FILESYSTEM_VERBS = {
    "cat",
    "less",
    "more",
    "head",
    "tail",
    "sed",
    "grep",
    "rg",
    "find",
    "ls",
    "dir",
    "stat",
    "du",
    "wc",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "touch",
    "tee",
    "printf",
    "echo",
}


def _rejects_workspace_escape(command: str) -> bool:
    suspicious = [
        "..",
        "/etc",
        "/var",
        "/tmp",
        "/proc",
        "/dev",
        "~",
    ]

    lowered = command.lower()
    return any(token in lowered for token in suspicious)


def _is_filesystem_operation(command: str) -> bool:
    lowered = command.lower()

    if any(op in lowered for op in (">>", ">", "<", "2>")):
        return True

    tokens = re.split(r"\s+|[;&|()]", lowered)
    first = tokens[0] if tokens else ""

    if first in {"pwd", "python", "pytest", "python3", "node", "npm", "pip"}:
        return False

    if any(token in FILESYSTEM_VERBS for token in tokens):
        return True

    return False


def run_command(command: str) -> str:
    if not command or not command.strip():
        return "Command is empty."

    if _rejects_workspace_escape(command):
        return "Command blocked: outside workspace."

    if re.search(r"(^|\s)(/|~|\.\./)", command):
        return "Command blocked: outside workspace."

    if _is_filesystem_operation(command):
        return "Command blocked: use read_file/write_file for filesystem access."

    console.print(f"[bold yellow]⚠ agent wants to run:[/bold yellow] [cyan]{command}[/cyan]")

    try:
        confirmed = Confirm.ask("Allow?", default=False)
    except EOFError:
        return "Command rejected by user."

    if not confirmed:
        return "Command rejected by user."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = []

        if result.stdout:
            output.append(
                "STDOUT:\n" + result.stdout
            )

        if result.stderr:
            output.append(
                "STDERR:\n" + result.stderr
            )

        output.append(
            f"EXIT_CODE={result.returncode}"
        )

        return "\n".join(output)

    except subprocess.TimeoutExpired:
        return "Command timed out after 120 seconds."