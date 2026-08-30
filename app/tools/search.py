from pathlib import Path

from app.indexer.search import search


def search_code(
    query: str,
    limit: int = 5,
) -> str:

    db_path = Path(".owa/index.db")

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

    output = []

    for result in results:

        output.append(
            f"FILE: {result['path']}\n"
            f"CHUNK: {result['chunk_index']}\n"
            f"SIMILARITY: {result['score']:.4f}\n"
            f"CONTENT:\n{result['content']}"
        )

    return "\n\n" + ("\n" + "-" * 70 + "\n\n").join(output)
