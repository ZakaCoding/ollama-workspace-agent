"""Local lexical signals shared by hybrid search and reranking."""

import re


def terms(text: str) -> set[str]:
    # Keep the full identifier as well as its snake_case / camelCase parts.
    words = re.findall(r"\w+", text, re.UNICODE)
    result = {word.lower() for word in words}
    for word in words:
        split = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", word)
        split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", split)
        result.update(part.lower() for part in re.split(r"[_\s]+", split) if part)
    return result


def coverage(query: str, text: str) -> float:
    query_terms = terms(query)
    return len(query_terms & terms(text)) / len(query_terms) if query_terms else 0.0


def _contains(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def exact_signals(query: str, path: str, content: str) -> dict[str, float]:
    query_text = " ".join(query.lower().split())
    content_text = " ".join(content.lower().split())
    phrases = re.findall(r'"([^"\n]+)"|`([^`\n]+)`', query)
    requested = [" ".join((quoted or code).lower().split()) for quoted, code in phrases]
    requested = [phrase for phrase in requested if phrase]
    phrase_score = (
        sum(_contains(content_text, phrase) for phrase in requested) / len(requested)
        if requested else float(bool(query_text) and _contains(content_text, query_text))
    )

    normalized_path = path.replace("\\", "/").lower()
    # Explicit paths must match a complete suffix; sharing an extension or a
    # directory is not a filename match.
    references = re.findall(r"[\w@-]+(?:[./\\][\w@-]+)+", query.lower())
    references = [ref.replace("\\", "/") for ref in references]
    if references:
        path_score = float(any(
            normalized_path == ref or normalized_path.endswith("/" + ref)
            for ref in references
        ))
    else:
        stem = normalized_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        path_score = float(bool(stem) and _contains(query_text, stem))

    # Exact identifier mentions also cover non-Python symbols. Declaration
    # matches receive an additional reranking signal in the caller.
    identifiers = re.findall(r"\b\w+\b", query)
    explicit = [word.lower() for word in identifiers if "_" in word or re.search(r"[a-z][A-Z]", word)]
    symbol_score = (
        sum(_contains(content_text, word) for word in explicit) / len(explicit)
        if explicit else 0.0
    )
    return {"phrase_score": phrase_score, "path_score": path_score, "symbol_score": symbol_score}
