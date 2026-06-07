from typing import Literal

ComparisonStatus = Literal[
    "AGREEMENT_THREAT",
    "AGREEMENT_SAFE",
    "SOURCE_STRICTER_THAN_JUDGE",
    "JUDGE_STRICTER_THAN_SOURCE",
    "REVIEW_REQUIRED",
    "EVALUATION_ERROR",
]


def compare_source_and_judge(
    source_verdict: str | None,
    judge_verdict: str | None,
    *,
    evaluation_error: bool = False,
) -> ComparisonStatus:
    if evaluation_error:
        return "EVALUATION_ERROR"

    normalized_source = _normalize_verdict(source_verdict)
    normalized_judge = _normalize_verdict(judge_verdict)

    if normalized_judge == "UNCERTAIN":
        return "REVIEW_REQUIRED"
    if normalized_source not in {"THREAT", "SAFE"} or normalized_judge not in {"THREAT", "SAFE"}:
        return "REVIEW_REQUIRED"
    if normalized_source == "THREAT" and normalized_judge == "THREAT":
        return "AGREEMENT_THREAT"
    if normalized_source == "SAFE" and normalized_judge == "SAFE":
        return "AGREEMENT_SAFE"
    if normalized_source == "THREAT" and normalized_judge == "SAFE":
        return "SOURCE_STRICTER_THAN_JUDGE"
    return "JUDGE_STRICTER_THAN_SOURCE"


def _normalize_verdict(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    if normalized in {"THREAT", "SAFE", "UNCERTAIN"}:
        return normalized
    return None
