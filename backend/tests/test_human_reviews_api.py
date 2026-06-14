from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    Dataset,
    EvaluationJob,
    EvaluationJobAttempt,
    JudgeResultRecord,
    PortkeyGatewayProfile,
    Project,
    Stream,
)


def _dataset_with_judge_results(db_session: Session) -> list[Attempt]:
    project = Project(name="Project")
    dataset = Dataset(
        project=project,
        scan_name="Review scan",
        source_content_type="application/json",
        detected_format="static_json",
        parser_version="static-json-v1",
        raw_payload=[],
        import_status="imported",
        stream_count=6,
        attempt_count=6,
        error_count=0,
    )
    db_session.add(dataset)
    db_session.flush()

    verdict_pairs = [
        ("THREAT", "SAFE"),
        ("SAFE", "THREAT"),
        ("THREAT", "SAFE"),
        ("SAFE", "THREAT"),
        ("THREAT", "SAFE"),
        ("SAFE", "SAFE"),
    ]
    attempts: list[Attempt] = []
    for index, (source_verdict, _judge_verdict) in enumerate(verdict_pairs):
        stream = Stream(
            dataset_id=dataset.id,
            input_type="static",
            raw_payload={},
            stream_metadata={},
        )
        db_session.add(stream)
        db_session.flush()
        attempt = Attempt(
            dataset_id=dataset.id,
            stream_id=stream.id,
            attempt_index=0,
            source_prompt=f"prompt {index}",
            source_output=f"output {index}",
            source_threat_raw=source_verdict,
            source_threat_normalized=source_verdict,
            raw_payload={},
            attempt_metadata={},
        )
        db_session.add(attempt)
        db_session.flush()
        attempts.append(attempt)

    profile = PortkeyGatewayProfile(
        profile_name="test profile",
        gateway_base_url="https://example.test/v1/chat/completions",
        portkey_api_key="pk-test-value",
        routing_mode="direct",
        judge_model="judge-model",
    )
    db_session.add(profile)
    db_session.flush()

    job = EvaluationJob(
        dataset_id=dataset.id,
        portkey_gateway_profile_id=profile.id,
        status="completed",
        retry_limit=0,
        total_attempts=len(attempts),
        processed_attempts=len(attempts),
        succeeded_attempts=len(attempts),
        failed_attempts=0,
    )
    db_session.add(job)
    db_session.flush()

    for attempt, (_source_verdict, judge_verdict) in zip(attempts, verdict_pairs, strict=True):
        job_attempt = EvaluationJobAttempt(
            job_id=job.id,
            dataset_id=dataset.id,
            stream_id=attempt.stream_id,
            attempt_id=attempt.id,
            status="succeeded",
            retry_count=0,
            max_retries=0,
        )
        db_session.add(job_attempt)
        db_session.flush()
        db_session.add(
            JudgeResultRecord(
                dataset_id=dataset.id,
                stream_id=attempt.stream_id,
                attempt_id=attempt.id,
                portkey_gateway_profile_id=profile.id,
                job_attempt_id=job_attempt.id,
                response_verdict=judge_verdict,
                confidence=0.8,
                response_behavior="UNSAFE_COMPLETION",
                comparison_status="REVIEW_REQUIRED",
                risk_category="SAFETY",
                explanation="fixture",
                raw_response={},
            )
        )

    db_session.commit()
    return attempts


def test_reviewer_can_confirm_source_judge_or_alarm_threat(
    client: TestClient, db_session: Session
) -> None:
    attempts = _dataset_with_judge_results(db_session)

    decisions = ["CONFIRM_SOURCE", "CONFIRM_JUDGE", "ALARM_THREAT"]
    for index, decision in enumerate(decisions):
        response = client.put(
            f"/results/attempts/{attempts[index].id}/review",
            json={
                "decision": decision,
                "reviewer_identity": f"reviewer-{index}",
                "comment": f"comment {index}",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["attempt_id"] == attempts[index].id
        assert body["decision"] == decision
        assert body["reviewer_identity"] == f"reviewer-{index}"
        assert body["comment"] == f"comment {index}"
        assert body["reviewed_at"] is not None


def test_review_comment_identity_and_timestamp_are_persisted(
    client: TestClient, db_session: Session
) -> None:
    attempts = _dataset_with_judge_results(db_session)

    create = client.put(
        f"/results/attempts/{attempts[0].id}/review",
        json={
            "decision": "CONFIRM_SOURCE",
            "reviewer_identity": "analyst@example.test",
            "comment": "source label is correct",
        },
    )
    assert create.status_code == 200

    read = client.get(f"/results/attempts/{attempts[0].id}/review")

    assert read.status_code == 200
    body = read.json()
    assert body["decision"] == "CONFIRM_SOURCE"
    assert body["reviewer_identity"] == "analyst@example.test"
    assert body["comment"] == "source label is correct"
    assert body["reviewed_at"] is not None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_result_explorer_filters_reviewed_and_unreviewed_attempts(
    client: TestClient, db_session: Session
) -> None:
    attempts = _dataset_with_judge_results(db_session)
    review = client.put(
        f"/results/attempts/{attempts[0].id}/review",
        json={
            "decision": "CONFIRM_SOURCE",
            "reviewer_identity": "analyst",
            "comment": None,
        },
    )
    assert review.status_code == 200

    reviewed = client.get("/results/attempts", params={"reviewed": True})
    unreviewed = client.get("/results/attempts", params={"reviewed": False})

    assert reviewed.status_code == 200
    assert unreviewed.status_code == 200
    assert reviewed.json()["total"] == 1
    assert reviewed.json()["items"][0]["review_decision"] == "CONFIRM_SOURCE"
    assert unreviewed.json()["total"] == 5


def test_reviewed_quality_metrics_use_only_adjudicated_records(
    client: TestClient, db_session: Session
) -> None:
    attempts = _dataset_with_judge_results(db_session)
    decisions = [
        "CONFIRM_SOURCE",
        "CONFIRM_SOURCE",
        "CONFIRM_JUDGE",
        "CONFIRM_JUDGE",
        "ALARM_THREAT",
    ]
    for index, decision in enumerate(decisions):
        response = client.put(
            f"/results/attempts/{attempts[index].id}/review",
            json={
                "decision": decision,
                "reviewer_identity": "analyst",
                "comment": None,
            },
        )
        assert response.status_code == 200

    response = client.get("/results/reviewed-quality")

    assert response.status_code == 200
    body = response.json()
    assert body["total_attempts"] == 6
    assert body["reviewed_cases"] == 5
    assert body["alarm_threat_cases"] == 1
    assert body["metric_cases"] == 5
    assert body["confirmed_tp"] == 2
    assert body["confirmed_tn"] == 1
    assert body["confirmed_fp"] == 1
    assert body["confirmed_fn"] == 1
    assert body["accuracy"] == 0.6
    assert body["precision"] == 2 / 3
    assert body["recall"] == 2 / 3
    assert body["f1_score"] == 2 / 3
    assert body["review_coverage"] == 5 / 6
