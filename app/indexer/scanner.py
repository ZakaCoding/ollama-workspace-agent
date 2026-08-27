from pathlib import Path


DEFAULT_IGNORES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "__pycache__",
    ".next",
    "dist",
    "build",
    "coverage",
}


def scan_workspace(
    workspace: Path,
    ignores: set[str] | None = None,
) -> list[Path]:

    workspace = workspace.resolve()
    ignores = ignores or DEFAULT_IGNORES

    files: list[Path] = []

    for path in workspace.rglob("*"):

        if not path.is_file():
            continue

        relative = path.relative_to(workspace)

        if any(
            part in ignores
            for part in relative.parts
        ):
            continue

        files.append(path)

    return sorted(files)
