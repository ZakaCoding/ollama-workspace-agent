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


# Patterns that indicate the model is narrating fake tool activity.
_FAKE_NARRATION_RE = re.compile(
    r"(?:I(?:'m| am) (?:checking|looking|searching|scanning|inspecting|reading|fetching|retrieving|running|executing)|Let me (?:check|look|search|scan|inspect|read|fetch|retrieve|run|execute)|I(?:'ll| will) (?:check|look|search|scan|inspect|read|fetch|retrieve|run|execute))",
    re.IGNORECASE,
)


def detect_fake_narration(content: str) -> VerificationResult:
    """Detect model text that narrates tool activity without a real tool call."""
    if _FAKE_NARRATION_RE.search(content):
        return VerificationResult(
            passed=False,
            message="Response contains fake tool narration.",
            should_retry=True,
        )
    return VerificationResult(passed=True, message="No fake narration detected.")


def verify_tool_result(
    tool_name: str,
    result: str,
) -> VerificationResult:

    if not result:
        return VerificationResult(
            passed=False,
            message="Tool returned an empty result.",
        )

    if "error" in result.lower():
        return VerificationResult(
            passed=False,
            message=result,
        )

    return VerificationResult(
        passed=True,
        message="Tool result received successfully.",
    )