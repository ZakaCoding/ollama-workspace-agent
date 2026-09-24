from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class VerificationResult:

    passed: bool
    message: str
    # When True, the caller should retry with a stricter evidence prompt.
    should_retry: bool = False
    # When True, the caller should refuse to answer rather than show the content.
    should_refuse: bool = False


# Matches path-like tokens: at least one slash or a known extension.
_PATH_RE = re.compile(
    r'(?:^|[\s`\'"\(])([\w./\-]+\.(?:py|js|ts|go|rs|java|c|cpp|h|md|yaml|yml|toml|json|sh|txt))',
    re.MULTILINE,
)

_CITATION_RE = re.compile(r"\[([^\]]+#chunk=\d+)\]")
_TERM_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{2,}")
_GENERIC_TERMS = {
    "about", "after", "also", "and", "answer", "because", "contains",
    "does", "file", "from", "here", "into", "more", "only", "repository",
    "that", "this", "uses", "with", "would", "your", "implemented",
    "implementation", "configured", "located", "defined", "function",
}


def _terms(text: str) -> set[str]:
    return {
        part
        for term in _TERM_RE.findall(text.lower())
        for part in term.split("_")
    }


def _extract_mentioned_paths(content: str) -> list[str]:
    return [m.group(1) for m in _PATH_RE.finditer(content)]


def validate_mentioned_paths(
    content: str,
    workspace: Path,
) -> VerificationResult:
    """Reject answers that mention file paths that do not exist in the workspace."""
    mentioned = _extract_mentioned_paths(content)
    missing = [
        p for p in mentioned
        if not (workspace / p).exists()
    ]
    if missing:
        return VerificationResult(
            passed=False,
            message=(
                f"Answer mentions path(s) that do not exist in the repository: "
                f"{', '.join(missing[:5])}."
            ),
            should_retry=True,
        )
    return VerificationResult(passed=True, message="All mentioned paths verified.")


def verify_evidence_citations(
    content: str,
    allowed_citations: set[str],
    require_citation: bool = False,
) -> VerificationResult:
    citations = set(re.findall(r"\[([^\]]+#chunk=\d+)\]", content))

    if require_citation and not citations:
        return VerificationResult(
            passed=False,
            message="Repository answer contains no evidence citation.",
            should_retry=True,
        )

    unsupported = citations - allowed_citations
    if unsupported:
        return VerificationResult(
            passed=False,
            message=(
                "Repository answer cites evidence not present in retrieved "
                f"context: {', '.join(sorted(unsupported))}."
            ),
            should_retry=True,
        )

    return VerificationResult(
        passed=True,
        message="Evidence citations are present and supported.",
    )


def detect_unsupported_claims(
    content: str,
    evidence_context: str,
) -> VerificationResult:
    """Detect claims that cite a real chunk but are absent from that chunk.

    This is intentionally a conservative lexical check. It does not try to
    replace model reasoning; it catches citation laundering, where a small
    model attaches a valid citation to an unrelated claim.
    """
    if not evidence_context:
        return VerificationResult(
            passed=True,
            message="No retrieved evidence was available for claim checking.",
        )

    for sentence in re.split(r"(?<=[.!?])\s+|\n+", content):
        citations = _CITATION_RE.findall(sentence)
        if not citations:
            continue

        for citation in citations:
            marker = f"EVIDENCE: [{citation}]"
            start = evidence_context.find(marker)
            if start < 0:
                continue

            end = evidence_context.find("\nEVIDENCE:", start + len(marker))
            section = evidence_context[start:] if end < 0 else evidence_context[start:end]

            claim = _CITATION_RE.sub("", sentence)
            claim_terms = _terms(claim)
            citation_terms = _terms(citation.split("#", 1)[0])
            evidence_terms = _terms(section)
            meaningful_claim_terms = claim_terms - citation_terms - _GENERIC_TERMS

            if meaningful_claim_terms and not meaningful_claim_terms & evidence_terms:
                return VerificationResult(
                    passed=False,
                    message=(
                        "Response makes a claim that is not supported by its "
                        f"cited evidence: [{citation}]."
                    ),
                    should_retry=True,
                )

    return VerificationResult(
        passed=True,
        message="Cited claims overlap with retrieved evidence.",
    )


# Patterns that indicate the model is narrating fake tool activity.
_FAKE_NARRATION_RE = re.compile(
    r"(?:I(?:'m| am) (?:checking|looking|searching|scanning|inspecting|reading|fetching|retrieving|running|executing)|Let me (?:check|look|search|scan|inspect|read|fetch|retrieve|run|execute)|I(?:'ll| will) (?:check|look|search|scan|inspect|read|fetch|retrieve|run|execute))",
    re.IGNORECASE,
)


def detect_fake_narration(content: str) -> VerificationResult:
    """Detect model text that narrates tool activity without a real tool call."""
    # Quoted repository examples are data, not promises to execute tools.
    prose = re.sub(r"```[\s\S]*?```", "", content)
    prose = re.sub(r"`[^`\n]*`", "", prose)
    prose = re.sub(r"(?m)^\s*>[^\n]*", "", prose)
    if _FAKE_NARRATION_RE.search(prose):
        return VerificationResult(
            passed=False,
            message="Response contains fake tool narration.",
            should_retry=True,
        )
    return VerificationResult(passed=True, message="No fake narration detected.")


def has_repeated_blocks(content: str) -> bool:
    """Catch prose/code loops without treating repeated short code lines as loops."""
    counts: dict[str, int] = {}
    for block in re.split(r"\n\s*\n", content):
        key = " ".join(block.lower().split())
        if len(key) < 40:
            continue
        counts[key] = counts.get(key, 0) + 1
        if counts[key] >= 3:
            return True
    return False


def verify_tool_result(
    tool_name: str,
    result: str,
) -> VerificationResult:

    if not result:
        return VerificationResult(
            passed=False,
            message="Tool returned an empty result.",
        )

    failure_prefixes = (
        "Tool blocked:", "Tool execution error:", "Unknown tool:",
        "Command blocked:", "Command rejected", "Command timed out", "Command is empty",
        "File does not exist:", "Directory does not exist:", "Not a file:", "Not a directory:",
        "File is not a UTF-8", "patch_file failed:", "File change rejected",
        "MCP tool call rejected", "MCP tool error:",
    )
    failed = result.startswith(failure_prefixes)
    if tool_name == "run_command":
        exit_code = re.search(r"(?:^|\n)EXIT_CODE=(-?\d+)\s*$", result)
        failed = failed or exit_code is None or int(exit_code.group(1)) != 0
    if failed:
        return VerificationResult(
            passed=False,
            message=result,
        )

    return VerificationResult(
        passed=True,
        message="Tool result received successfully.",
    )
