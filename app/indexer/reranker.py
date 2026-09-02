import re


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


_SYMBOL_RE = re.compile(r"(?:def |class |async def )([\w]+)", re.MULTILINE)
_ROUTE_RE = re.compile(r"@(?:app|router)\.(?:get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", re.MULTILINE)


def _symbol_terms(content: str) -> set[str]:
    """Extract function/class names and route paths from content."""
    symbols = set(_SYMBOL_RE.findall(content))
    routes = set(_ROUTE_RE.findall(content))
    return {s.lower() for s in symbols | routes}


def rerank(query: str, results: list[dict], limit: int) -> list[dict]:
    """Rerank a small candidate set locally without another model call."""
    query_terms = _terms(query)
    query_text = " ".join(query.lower().split())
    # Extract symbols from query (e.g. function names typed by user)
    query_symbols = _symbol_terms(query) | query_terms

    for result in results:
        content = result.get("content", "")
        path = result.get("path", "")
        content_terms = _terms(content)
        path_terms = _terms(path.replace("/", " ").replace(".", " "))
        content_symbols = _symbol_terms(content)

        exact_terms = (
            len(query_terms & content_terms) / len(query_terms)
            if query_terms
            else 0.0
        )
        phrase_match = float(query_text in content.lower()) if query_text else 0.0
        # Filename match: query terms appear in the file path
        path_match = float(bool(query_terms & path_terms))
        # Symbol match: query mentions a function/class name present in content
        symbol_match = (
            len(query_symbols & content_symbols) / len(query_symbols)
            if query_symbols
            else 0.0
        )
        # Neighboring chunk bonus: chunk_index 0 or 1 is often more relevant
        proximity_bonus = 0.05 if result.get("chunk_index", 99) <= 1 else 0.0

        result["rerank_score"] = (
            0.40 * result.get("score", 0.0)
            + 0.20 * exact_terms
            + 0.15 * symbol_match
            + 0.10 * phrase_match
            + 0.10 * path_match
            + proximity_bonus
        )

    return sorted(
        results,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )[:limit]