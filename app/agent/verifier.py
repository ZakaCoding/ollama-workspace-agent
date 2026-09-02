from dataclasses import dataclass
import re


@dataclass
class VerificationResult:

    passed: bool

    message: str


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
        )

    unsupported = citations - allowed_citations
    if unsupported:
        return VerificationResult(
            passed=False,
            message=(
                "Repository answer cites evidence not present in retrieved "
                f"context: {', '.join(sorted(unsupported))}."
            ),
        )

    return VerificationResult(
        passed=True,
        message="Evidence citations are present and supported.",
    )


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