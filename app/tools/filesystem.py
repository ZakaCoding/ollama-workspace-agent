from pathlib import Path


WORKSPACE = Path.cwd().resolve()


def resolve_path(path: str) -> Path:
    raw = Path(path)

    # Absolute paths are NOT allowed.
    if raw.is_absolute():
        raise PermissionError(
            f"Absolute paths are not allowed: {path}"
        )

    target = (WORKSPACE / raw).resolve()

    # Prevent ../workspace escape.
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise PermissionError(
            f"Path escapes workspace: {path}"
        )

    return target


def list_dir(path: str = ".") -> str:
    target = resolve_path(path)

    if not target.exists():
        return f"Directory does not exist: {path}"

    if not target.is_dir():
        return f"Not a directory: {path}"

    items = []

    for item in sorted(target.iterdir()):
        prefix = "DIR " if item.is_dir() else "FILE"
        items.append(f"{prefix} {item.name}")

    return "\n".join(items) or "(empty)"


def read_file(path: str) -> str:
    target = resolve_path(path)

    if not target.exists():
        return f"File does not exist: {path}"

    if not target.is_file():
        return f"Not a file: {path}"

    try:
        content = target.read_text(
            encoding="utf-8"
        )
    except UnicodeDecodeError:
        return "File is not a UTF-8 text file."

    max_chars = 30000

    if len(content) > max_chars:
        content = (
            content[:max_chars]
            + "\n\n[TRUNCATED]"
        )

    return content


def write_file(path: str, content: str) -> str:
    target = resolve_path(path)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    target.write_text(
        content,
        encoding="utf-8",
    )

    return (
        f"Successfully wrote {len(content)} "
        f"characters to {path}"
    )