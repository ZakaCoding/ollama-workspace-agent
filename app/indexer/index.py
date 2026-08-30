from pathlib import Path

from rich.console import Console

from app.indexer.chunker import chunk_text
from app.indexer.database import connect, initialize
from app.indexer.embeddings import embed
from app.indexer.store import save_chunk

console = Console(stderr=True)


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    ".owa",
}


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".php",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".css",
    ".scss",
    ".html",
    ".blade.php",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".sql",
    ".sh",
}


def _load_owaignore(workspace: Path) -> set[str]:
    owaignore = workspace / ".owaignore"
    if not owaignore.exists():
        return set()
    patterns = set()
    for line in owaignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.add(line)
    return patterns


def should_index(path: Path, workspace: Path | None = None, ignored_patterns: set[str] | None = None) -> bool:

    if not path.is_file():
        return False

    if any(part in IGNORED_DIRS for part in path.parts):
        return False

    if ignored_patterns and workspace:
        rel = path.relative_to(workspace)
        for pattern in ignored_patterns:
            if rel.match(pattern) or any(part == pattern for part in rel.parts):
                return False

    return path.suffix.lower() in TEXT_EXTENSIONS


def _ensure_gitignore(workspace: Path):
    gitignore = workspace / ".gitignore"
    entry = ".owa/\n"
    if gitignore.exists():
        if ".owa" in gitignore.read_text():
            return
        gitignore.open("a").write(f"\n{entry}")
    else:
        gitignore.write_text(entry)
    console.print("[dim]added .owa/ to .gitignore[/dim]")


def index_project(
    workspace: Path,
    db_path: Path,
):

    workspace = workspace.resolve()

    first_run = not db_path.exists()

    ignored_patterns = _load_owaignore(workspace)
    if ignored_patterns:
        console.print(f"[dim].owaignore: excluding {len(ignored_patterns)} pattern(s)[/dim]")

    initialize(db_path)

    with connect(db_path) as db:

        files = [
            path
            for path in workspace.rglob("*")
            if should_index(path, workspace, ignored_patterns)
        ]

        console.print(f"[dim]found {len(files)} files to index[/dim]")

        for file_path in files:

            relative_path = file_path.relative_to(
                workspace
            )

            try:
                content = file_path.read_text(
                    encoding="utf-8"
                )
            except (
                UnicodeDecodeError,
                OSError,
            ):
                console.print(f"[dim]skip {relative_path}[/dim]")
                continue

            chunks = chunk_text(content)

            console.print(f"[dim]indexing {relative_path} ({len(chunks)} chunks)[/dim]")

            for index, chunk in enumerate(chunks):

                vector = embed(chunk)

                save_chunk(
                    db=db,
                    path=str(relative_path),
                    chunk_index=index,
                    content=chunk,
                    embedding=vector,
                )

    console.print("[dim]index complete[/dim]")

    if first_run:
        _ensure_gitignore(workspace)
        console.print("[dim]tip: .owa/ holds the local index — add it to .gitignore if not done automatically[/dim]")
