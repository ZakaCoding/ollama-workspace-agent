import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from rich.console import Console

from app.indexer.chunker import chunk_text
from app.indexer.database import connect, initialize
from app.indexer.embeddings import embed_batch
from app.indexer.store import save_chunk

console = Console(stderr=True)


IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    ".owa",
    ".github",
    ".gitlab",
    "dist",
    "build",
    "out",
    "coverage",
    ".next",
    ".nuxt",
    ".cache",
    "vendor",
    "target",
    "bin",
    "obj",
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


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_indexed_hashes(db_path: Path) -> dict[str, str]:
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT DISTINCT path, file_hash FROM documents WHERE file_hash IS NOT NULL"
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def _delete_removed_files(db_path: Path, current_paths: set[str]) -> set[str]:
    with connect(db_path) as db:
        indexed = {
            row[0]
            for row in db.execute("SELECT DISTINCT path FROM documents").fetchall()
        }
        removed = indexed - current_paths
        for path in removed:
            db.execute("DELETE FROM documents WHERE path = ?", (path,))
        if removed:
            db.commit()
    return removed


def _index_file(
    file_path: Path,
    relative_path: str,
    current_hash: str,
    db_path: Path,
) -> str:
    """Read, chunk, batch-embed, and save one file. Returns relative_path on success."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""

    chunks = chunk_text(content)
    if not chunks:
        return ""

    vectors = embed_batch(chunks)

    with connect(db_path) as db:
        for index, (chunk, vector) in enumerate(zip(chunks, vectors)):
            save_chunk(
                db=db,
                path=relative_path,
                chunk_index=index,
                content=chunk,
                embedding=vector,
                file_hash=current_hash,
            )

    return relative_path


def index_project(
    workspace: Path,
    db_path: Path,
    workers: int = 4,
):
    workspace = workspace.resolve()
    first_run = not db_path.exists()

    ignored_patterns = _load_owaignore(workspace)
    if ignored_patterns:
        console.print(f"[dim].owaignore: excluding {len(ignored_patterns)} pattern(s)[/dim]")

    initialize(db_path)

    files = [
        path
        for path in workspace.rglob("*")
        if should_index(path, workspace, ignored_patterns)
    ]

    current_rel_paths = {str(f.relative_to(workspace)) for f in files}

    removed = _delete_removed_files(db_path, current_rel_paths)
    if removed:
        console.print(f"[dim]removed {len(removed)} deleted file(s) from index[/dim]")

    indexed_hashes = _load_indexed_hashes(db_path)

    pending = []
    skipped = 0

    for file_path in files:
        relative_path = str(file_path.relative_to(workspace))
        try:
            current_hash = _file_hash(file_path)
        except OSError:
            continue
        if indexed_hashes.get(relative_path) == current_hash:
            skipped += 1
        else:
            pending.append((file_path, relative_path, current_hash))

    updated = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_index_file, fp, rp, fh, db_path): rp
            for fp, rp, fh in pending
        }
        for future in as_completed(futures):
            rel = futures[future]
            try:
                result = future.result()
                if result:
                    console.print(f"[dim]indexed {result}[/dim]")
                    updated += 1
                else:
                    console.print(f"[dim]skip {rel} (unreadable)[/dim]")
                    failed += 1
            except Exception as exc:
                console.print(f"[dim]error {rel}: {exc}[/dim]")
                failed += 1

    parts = [f"{updated} updated", f"{skipped} unchanged"]
    if failed:
        parts.append(f"{failed} failed")
    console.print(f"[dim]index complete — {', '.join(parts)}[/dim]")

    if first_run:
        _ensure_gitignore(workspace)
        console.print("[dim]tip: .owa/ holds the local index — add it to .gitignore if not done automatically[/dim]")
