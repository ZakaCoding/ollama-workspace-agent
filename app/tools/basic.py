from pathlib import Path
import subprocess


WORKSPACE = Path.cwd().resolve()


def _safe_path(path: str) -> Path:
    """Resolve a path and ensure it stays inside the workspace."""
    target = (WORKSPACE / path).resolve()

    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise PermissionError(
            f"Access denied: {target} is outside workspace {WORKSPACE}"
        )

    return target


def list_dir(path: str = ".") -> str:
    target = _safe_path(path)

    if not target.exists():
        return f"Path does not exist: {path}"

    if not target.is_dir():
        return f"Not a directory: {path}"

    entries = []

    for item in sorted(target.iterdir()):
        prefix = "DIR " if item.is_dir() else "FILE"
        entries.append(f"{prefix} {item.name}")

    return "\n".join(entries) or "(empty directory)"


def read_file(path: str) -> str:
    target = _safe_path(path)

    if not target.exists():
        return f"File does not exist: {path}"

    if not target.is_file():
        return f"Not a file: {path}"

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Cannot read {path}: not a UTF-8 text file."

    # Prevent accidentally dumping giant files into context.
    max_chars = 20000

    if len(content) > max_chars:
        content = (
            content[:max_chars]
            + f"\n\n[TRUNCATED: file is larger than {max_chars} characters]"
        )

    return content


def run_command(command: str) -> str:
    """
    Execute a command inside the agent workspace.

    This is intentionally guarded by a confirmation prompt.
    """

    print("\n" + "=" * 70)
    print("⚠️  AGENT WANTS TO EXECUTE:")
    print(command)
    print("=" * 70)

    answer = input("Allow command? [y/N]: ").strip().lower()

    if answer != "y":
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
            output.append("STDOUT:\n" + result.stdout)

        if result.stderr:
            output.append("STDERR:\n" + result.stderr)

        output.append(f"\nEXIT CODE: {result.returncode}")

        return "\n".join(output)

    except subprocess.TimeoutExpired:
        return "Command timed out after 120 seconds."