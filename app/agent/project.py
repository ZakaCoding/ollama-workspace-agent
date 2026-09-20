"""Bounded, current-file grounding for project orientation requests."""

from itertools import islice
from pathlib import Path
import re

from app.indexer.index import iter_project_files


def is_project_learning_request(task: str) -> bool:
    normalized = " ".join(task.lower().split())
    return bool(
        re.search(r"\b(?:learn|understand|familiarize|familiarise|explore|overview)\b", normalized)
        and re.search(r"\b(?:project|repo|repository|codebase|markdown|md)\b", normalized)
    ) or bool(re.search(r"\bread\s+all\s+(?:the\s+)?(?:markdown|md)\b", normalized))


def build_project_context(workspace: Path, builder) -> tuple[str, set[str]]:
    workspace = workspace.resolve()
    # Limit traversal and prompt size independently of repository size.
    candidates = list(islice(iter_project_files(workspace), 2001))
    scan_limited = len(candidates) > 2000
    candidates = candidates[:2000]
    priority = {
        "readme.md": 0, "pyproject.toml": 1, "package.json": 1,
        "cargo.toml": 1, "go.mod": 1, "main.py": 2,
        "architecture.md": 3, "development_plan.md": 4,
    }
    candidates.sort(key=lambda p: (
        priority.get(p.name.lower(), 5 if p.suffix.lower() == ".md" else 6),
        len(p.relative_to(workspace).parts), str(p.relative_to(workspace)),
    ))
    # A brief should be useful even under the smallest configured context.
    results = []
    budget = builder.max_chars
    paths = [str(p.relative_to(workspace)) for p in candidates]
    inventory = "\n".join(paths[:40])[:min(1600, budget // 5)]
    selected = []
    used = len(inventory) + 600
    for path in candidates:
        if len(results) >= 6 or budget - used < 400:
            break
        relative = str(path.relative_to(workspace))
        prefix = (
            f"EVIDENCE: [{relative}#chunk=0]\nFILE: {relative}\n"
            f"CITE THIS EVIDENCE AS: [{relative}#chunk=0]\nCONTENT:\n"
        )
        limit = min(1800, budget - used - len(prefix) - 32)
        if limit < 100:
            continue
        try:
            with path.open("rb") as source:
                raw = source.read(limit + 1)
            content = raw[:limit].decode("utf-8", errors="replace")
        except OSError:
            continue
        if not content.strip() or "\x00" in content:
            continue
        excerpt = (
            prefix + content + "\n"
            + ("[excerpt truncated]\n" if len(raw) > limit else "")
        )
        results.append(excerpt)
        selected.append(relative)
        used += len(excerpt)
    if not results:
        return "", set()
    context = (
        "PROJECT OVERVIEW — current files, read-only\n"
        f"Inspected excerpts from {len(selected)} files; discovered "
        f"{'at least ' if scan_limited else ''}{len(candidates)} eligible files. "
        "This is a bounded overview, not a claim to have read every file.\n"
        "File inventory (possibly abbreviated):\n" + inventory
        + "\n\n" + "\n".join(results)
    )
    return context, {f"{path}#chunk=0" for path in selected}
