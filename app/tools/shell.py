from app.workspace import current_workspace
import os
import re
import subprocess

from app.tools.filesystem import WORKSPACE
from app.tools.approval import approve



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

    if not approve("command", command, variable="OWA_COMMAND_APPROVAL"):
        return "Command rejected by user."

    sandbox = os.getenv("OWA_COMMAND_SANDBOX", "docker").lower()
    if sandbox not in {"docker", "host"}:
        return "Command blocked: invalid OWA_COMMAND_SANDBOX setting."

    workspace = current_workspace(WORKSPACE)
    if sandbox == "docker":
        docker_command = [
            "docker", "run", "--rm", "--pull", "never", "--network", "none", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--pids-limit", "128",
            "--memory", "1g", "--cpus", "2", "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--mount", f"type=bind,src={workspace},dst=/workspace",
            "--workdir", "/workspace",
        ]
        if hasattr(os, "getuid"):
            docker_command += ["--user", f"{os.getuid()}:{os.getgid()}"]
        docker_command += [os.getenv("OWA_SANDBOX_IMAGE", "python:3.12-slim"), "sh", "-lc", command]
    else:
        docker_command = None

    try:
        result = subprocess.run(
            docker_command if docker_command is not None else command,
            shell=sandbox == "host",
            cwd=workspace,
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
    except FileNotFoundError:
        return "Command blocked: Docker is unavailable. Install Docker or explicitly set OWA_COMMAND_SANDBOX=host."
