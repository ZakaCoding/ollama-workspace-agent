from dataclasses import dataclass


@dataclass
class VerificationResult:

    passed: bool

    message: str


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