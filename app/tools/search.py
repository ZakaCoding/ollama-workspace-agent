from pathlib import Path
from app.workspace import current_workspace

from app.indexer.search import search


def search_code(
    query: str,
    limit: int = 5,
) -> str:
    from app.agent.context import ContextBuilder

    db_path = current_workspace() / ".owa" / "index.db"

    if not db_path.exists():
        return (
            "Project index does not exist. "
            "Run the project indexer first."
        )

    results = search(
        db_path,
        query,
        limit,
    )

    if not results:
        return "No relevant code found."

    builder = ContextBuilder(max_results=min(limit, 5))
    # Include citation headers in the per-tool cap so storage need not clip them.
    builder.max_chars = min(builder.max_chars, builder.max_chunk_chars)
    context = builder.build(results, query=query, tool_output=True)
    return context or "No relevant code found."
