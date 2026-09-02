import re


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def rerank(query: str, results: list[dict], limit: int) -> list[dict]:
    """Rerank a small candidate set locally without another model call."""
    query_terms = _terms(query)
    query_text = " ".join(query.lower().split())

    for result in results:
        content = result.get("content", "")
        path = result.get("path", "")
        content_terms = _terms(content)
        path_terms = _terms(path.replace("/", " "))
        exact_terms = (
            len(query_terms & content_terms) / len(query_terms)
            if query_terms
            else 0.0
        )
        phrase_match = float(query_text in content.lower()) if query_text else 0.0
        path_match = float(bool(query_terms & path_terms))
        result["rerank_score"] = (
            0.55 * result.get("score", 0.0)
            + 0.25 * exact_terms
            + 0.15 * phrase_match
            + 0.05 * path_match
        )

    return sorted(
        results,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )[:limit]