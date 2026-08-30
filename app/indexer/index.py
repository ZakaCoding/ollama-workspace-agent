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
    ".ai",
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


def should_index(path: Path) -> bool:

    if not path.is_file():
        return False

    if any(
        part in IGNORED_DIRS
        for part in path.parts
    ):
        return False

    return (
        path.suffix.lower()
        in TEXT_EXTENSIONS
    )


def index_project(
    workspace: Path,
    db_path: Path,
):

    workspace = workspace.resolve()

    initialize(db_path)

    with connect(db_path) as db:

        files = [
            path
            for path in workspace.rglob("*")
            if should_index(path)
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
