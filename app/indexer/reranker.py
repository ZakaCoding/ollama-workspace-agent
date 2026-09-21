import re

from app.indexer.relevance import coverage, exact_signals, terms


_SYMBOL_RE = re.compile(r"(?:def |class |async def )([\w]+)", re.MULTILINE)
_ROUTE_RE = re.compile(r"@(?:app|router)\.(?:get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", re.MULTILINE)


def _symbol_terms(content: str) -> set[str]:
    """Extract function/class names and route paths from content."""
    symbols = set(_SYMBOL_RE.findall(content))
    routes = set(_ROUTE_RE.findall(content))
    return {s.lower() for s in symbols | routes}


def rerank(query: str, results: list[dict], limit: int) -> list[dict]:
    """Rerank a small candidate set locally without another model call."""
    if limit <= 0:
        return []
    query_terms = terms(query)
    for result in results:
        content = result.get("content", "")
        path = result.get("path", "")
        signals = exact_signals(query, path, content)
        content_symbols = _symbol_terms(content)
        declaration_match = float(bool(query_terms & content_symbols))
        exact_terms = coverage(query, content)
        phrase_match = signals["phrase_score"]
        path_match = signals["path_score"]
        symbol_match = max(signals["symbol_score"], declaration_match)
        result.update(signals)
        # Neighboring chunk bonus: chunk_index 0 or 1 is often more relevant
        proximity_bonus = 0.05 if result.get("chunk_index", 99) <= 1 else 0.0

        result["rerank_score"] = (
            0.30 * result.get("score", 0.0)
            + 0.10 * exact_terms
            + 0.15 * symbol_match
            + 0.20 * phrase_match
            + 0.20 * path_match
            + proximity_bonus
        )

    return sorted(
        results,
        key=lambda item: item["rerank_score"],
        reverse=True,
    )[:limit]
