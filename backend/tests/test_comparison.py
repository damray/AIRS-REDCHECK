import pytest

from app.services.comparison import compare_source_and_judge


@pytest.mark.parametrize(
    ("source_verdict", "judge_verdict", "expected"),
    [
        ("THREAT", "THREAT", "AGREEMENT_THREAT"),
        ("SAFE", "SAFE", "AGREEMENT_SAFE"),
        ("THREAT", "SAFE", "SOURCE_STRICTER_THAN_JUDGE"),
        ("SAFE", "THREAT", "JUDGE_STRICTER_THAN_SOURCE"),
        ("THREAT", "UNCERTAIN", "REVIEW_REQUIRED"),
        ("SAFE", "UNCERTAIN", "REVIEW_REQUIRED"),
        (None, "THREAT", "REVIEW_REQUIRED"),
        ("UNKNOWN", "SAFE", "REVIEW_REQUIRED"),
    ],
)
def test_comparison_matrix_branches(
    source_verdict: str | None,
    judge_verdict: str,
    expected: str,
) -> None:
    assert compare_source_and_judge(source_verdict, judge_verdict) == expected


def test_evaluation_error_comparison_status() -> None:
    assert compare_source_and_judge("THREAT", None, evaluation_error=True) == "EVALUATION_ERROR"
