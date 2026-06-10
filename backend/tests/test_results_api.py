from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    Dataset,
    EvaluationError,
    EvaluationJob,
    EvaluationJobAttempt,
    HumanReview,
    JudgeResultRecord,
    PortkeyGatewayProfile,
    Project,
    Stream,
)


def _dataset_with_results(
    db_session: Session, project_name: str = "Project"
) -> tuple[Dataset, list[Stream], list[Attempt]]:
    project = Project(name=project_name)
    dataset = Dataset(
        project=project,
        scan_name=f"{project_name} scan",
        source_content_type="application/json",
        detected_format="agent_json",
        parser_version="agent-json-v1",
        raw_payload=[],
        import_status="imported",
        stream_count=2,
        attempt_count=3,
        error_count=0,
    )
    db_session.add(dataset)
    db_session.flush()

    agent_stream = Stream(
        dataset_id=dataset.id,
        external_stream_id="agent-stream",
        input_type="agent",
        goal="agent goal",
        raw_payload={},
        stream_metadata={},
    )
    static_stream = Stream(
        dataset_id=dataset.id,
        input_type="static",
        raw_payload={},
        stream_metadata={},
    )
    db_session.add_all([agent_stream, static_stream])
    db_session.flush()

    attempts = [
        Attempt(
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_index=2,
            source_prompt="agent prompt 2",
            source_output="agent output 2",
            source_threat_raw="True",
            source_threat_normalized="THREAT",
            raw_payload={},
            attempt_metadata={
                "category": "SAFETY",
                "severity": "HIGH",
                "techniques": ["PERSONA", "ROLEPLAY"],
            },
        ),
        Attempt(
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_index=1,
            source_prompt="agent prompt 1",
            source_output="agent output 1",
            source_threat_raw="False",
            source_threat_normalized="SAFE",
            raw_payload={},
            attempt_metadata={"category": "SECURITY", "severity": "LOW", "techniques": "DIRECT"},
        ),
        Attempt(
            dataset_id=dataset.id,
            stream_id=static_stream.id,
            attempt_index=0,
            source_prompt="static prompt",
            source_output="static output",
            source_threat_raw="False",
            source_threat_normalized="SAFE",
            raw_payload={},
            attempt_metadata={"category": "SAFETY", "severity": "LOW"},
        ),
    ]
    db_session.add_all(attempts)
    db_session.flush()

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
        total_attempts=2,
        processed_attempts=2,
        succeeded_attempts=2,
        failed_attempts=0,
    )
    db_session.add(job)
    db_session.flush()

    job_attempts = [
        EvaluationJobAttempt(
            job_id=job.id,
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_id=attempts[0].id,
            status="succeeded",
            retry_count=0,
            max_retries=0,
        ),
        EvaluationJobAttempt(
            job_id=job.id,
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_id=attempts[1].id,
            status="succeeded",
            retry_count=0,
            max_retries=0,
        ),
    ]
    db_session.add_all(job_attempts)
    db_session.flush()

    db_session.add(
        JudgeResultRecord(
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_id=attempts[0].id,
            portkey_gateway_profile_id=profile.id,
            job_attempt_id=job_attempts[0].id,
            response_verdict="SAFE",
            confidence=0.8,
            response_behavior="SAFE_REFUSAL",
            comparison_status="SOURCE_STRICTER_THAN_JUDGE",
            risk_category="SAFETY",
            explanation="refused",
            raw_response={},
        )
    )
    db_session.add(
        JudgeResultRecord(
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_id=attempts[1].id,
            portkey_gateway_profile_id=profile.id,
            job_attempt_id=job_attempts[1].id,
            response_verdict="THREAT",
            confidence=0.7,
            response_behavior="UNSAFE_COMPLETION",
            comparison_status="JUDGE_STRICTER_THAN_SOURCE",
            risk_category="SECURITY",
            explanation="unsafe",
            raw_response={},
        )
    )
    db_session.add(
        EvaluationError(
            dataset_id=dataset.id,
            stream_id=static_stream.id,
            attempt_id=attempts[2].id,
            error_code="invalid_judge_response",
            comparison_status="EVALUATION_ERROR",
            message="bad output",
            raw_response={},
        )
    )
    db_session.add(
        HumanReview(
            dataset_id=dataset.id,
            stream_id=agent_stream.id,
            attempt_id=attempts[0].id,
            decision="CONFIRM_SOURCE",
            reviewer_identity="analyst",
            comment="reviewed",
        )
    )
    db_session.commit()
    return dataset, [agent_stream, static_stream], attempts


def test_export_normalized_results_csv(client: TestClient, db_session: Session) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/export/normalized.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "airs-redcheck-normalized-results.csv" in response.headers["content-disposition"]
    body = response.text
    assert "attempt_id,dataset_id,stream_id" in body
    assert "agent prompt 2" in body
    assert "static output" in body
    assert body.count("\n") == 4


def test_export_disagreements_csv(client: TestClient, db_session: Session) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/export/disagreements.csv")

    assert response.status_code == 200
    body = response.text
    assert "SOURCE_STRICTER_THAN_JUDGE" in body
    assert "JUDGE_STRICTER_THAN_SOURCE" in body
    assert "EVALUATION_ERROR" not in body
    assert body.count("\n") == 3


def test_export_reviewed_cases_csv(client: TestClient, db_session: Session) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/export/reviewed.csv")

    assert response.status_code == 200
    body = response.text
    assert "CONFIRM_SOURCE" in body
    assert "analyst" in body
    assert "agent prompt 1" not in body
    assert body.count("\n") == 2


def test_export_current_view_supports_multiple_comparison_statuses(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/export/current.csv",
        params=[
            ("comparison_status", "SOURCE_STRICTER_THAN_JUDGE"),
            ("comparison_status", "JUDGE_STRICTER_THAN_SOURCE"),
        ],
    )

    assert response.status_code == 200
    assert "airs-redcheck-filtered-results.csv" in response.headers["content-disposition"]
    body = response.text
    assert "SOURCE_STRICTER_THAN_JUDGE" in body
    assert "JUDGE_STRICTER_THAN_SOURCE" in body
    assert "EVALUATION_ERROR" not in body
    assert body.count("\n") == 3


def test_export_current_view_supports_agreed_threats(
    client: TestClient, db_session: Session
) -> None:
    _, _, attempts = _dataset_with_results(db_session)
    profile = db_session.query(PortkeyGatewayProfile).one()
    job = db_session.query(EvaluationJob).one()
    job_attempt = EvaluationJobAttempt(
        job_id=job.id,
        dataset_id=attempts[2].dataset_id,
        stream_id=attempts[2].stream_id,
        attempt_id=attempts[2].id,
        status="succeeded",
        retry_count=0,
        max_retries=0,
    )
    db_session.add(job_attempt)
    db_session.flush()
    db_session.add(
        JudgeResultRecord(
            dataset_id=attempts[2].dataset_id,
            stream_id=attempts[2].stream_id,
            attempt_id=attempts[2].id,
            portkey_gateway_profile_id=profile.id,
            job_attempt_id=job_attempt.id,
            response_verdict="THREAT",
            confidence=0.9,
            response_behavior="UNSAFE_COMPLETION",
            comparison_status="AGREEMENT_THREAT",
            risk_category="SAFETY",
            explanation="unsafe",
            raw_response={},
        )
    )
    db_session.commit()

    response = client.get(
        "/results/export/current.csv",
        params={"comparison_status": "AGREEMENT_THREAT"},
    )

    assert response.status_code == 200
    body = response.text
    assert "AGREEMENT_THREAT" in body
    assert "static prompt" in body
    assert "SOURCE_STRICTER_THAN_JUDGE" not in body
    assert body.count("\n") == 2


def test_export_current_view_supports_reviewed_filter(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/export/current.csv", params={"reviewed": "true"})

    assert response.status_code == 200
    body = response.text
    assert "CONFIRM_SOURCE" in body
    assert "analyst" in body
    assert "agent prompt 1" not in body
    assert body.count("\n") == 2


def test_export_current_view_supports_combined_filters(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/export/current.csv",
        params={
            "comparison_status": "SOURCE_STRICTER_THAN_JUDGE",
            "source_verdict": "THREAT",
            "severity": "HIGH",
            "category": "SAFETY",
            "input_type": "agent",
            "technique": "PERSONA",
        },
    )

    assert response.status_code == 200
    body = response.text
    assert "agent prompt 2" in body
    assert "SOURCE_STRICTER_THAN_JUDGE" in body
    assert "agent prompt 1" not in body
    assert "static prompt" not in body
    assert body.count("\n") == 2


def test_results_are_filterable_by_comparison_status(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/attempts",
        params={"comparison_status": "SOURCE_STRICTER_THAN_JUDGE"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["comparison_status"] == "SOURCE_STRICTER_THAN_JUDGE"


def test_results_and_summaries_are_project_scoped(client: TestClient, db_session: Session) -> None:
    dataset_a, _, _ = _dataset_with_results(db_session, project_name="Project A")
    dataset_b, _, _ = _dataset_with_results(db_session, project_name="Project B")

    response = client.get("/results/attempts", params={"project_id": dataset_a.project_id})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert {item["dataset_id"] for item in body["items"]} == {dataset_a.id}

    summary = client.get(
        "/results/triage-summary", params={"project_id": dataset_a.project_id}
    ).json()
    assert summary["total_attempts"] == 3
    assert summary["errors"] == 1

    quality = client.get(
        "/results/reviewed-quality", params={"project_id": dataset_a.project_id}
    ).json()
    assert quality["total_attempts"] == 3
    assert quality["reviewed_cases"] == 1

    exported = client.get(
        "/results/export/normalized.csv", params={"project_id": dataset_a.project_id}
    )
    assert exported.status_code == 200
    assert dataset_a.id in exported.text
    assert dataset_b.id not in exported.text


def test_result_list_uses_excerpts_and_detail_returns_full_text(
    client: TestClient, db_session: Session
) -> None:
    _, _, attempts = _dataset_with_results(db_session)
    full_output = "large model output " * 100
    attempts[0].source_output = full_output
    db_session.commit()

    list_response = client.get(
        "/results/attempts",
        params={"comparison_status": "SOURCE_STRICTER_THAN_JUDGE"},
    )

    assert list_response.status_code == 200
    list_item = list_response.json()["items"][0]
    assert list_item["source_output"].endswith("...")
    assert len(list_item["source_output"]) == 500
    assert list_item["source_output"] != full_output

    detail_response = client.get(f"/results/attempts/{attempts[0].id}")

    assert detail_response.status_code == 200
    assert detail_response.json()["source_output"] == full_output


def test_export_keeps_full_text(client: TestClient, db_session: Session) -> None:
    _, _, attempts = _dataset_with_results(db_session)
    full_output = "large exported output " * 40
    attempts[0].source_output = full_output
    db_session.commit()

    response = client.get("/results/export/normalized.csv")

    assert response.status_code == 200
    assert full_output in response.text


def test_results_are_filterable_by_multiple_comparison_statuses(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/attempts",
        params=[
            ("comparison_status", "SOURCE_STRICTER_THAN_JUDGE"),
            ("comparison_status", "JUDGE_STRICTER_THAN_SOURCE"),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["comparison_status"] for item in body["items"]} == {
        "SOURCE_STRICTER_THAN_JUDGE",
        "JUDGE_STRICTER_THAN_SOURCE",
    }


def test_results_error_filter_returns_safe_error_metadata(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/attempts",
        params={"comparison_status": "EVALUATION_ERROR"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    error_row = body["items"][0]
    assert error_row["comparison_status"] == "EVALUATION_ERROR"
    assert error_row["source_prompt"] == "static prompt"
    assert error_row["source_output"] == "static output"
    assert error_row["evaluation_error_code"] == "invalid_judge_response"
    assert error_row["evaluation_error_message"] == "bad output"
    assert error_row["evaluation_error_created_at"] is not None
    assert "raw_response" not in error_row


def test_results_are_filterable_by_source_and_judge_verdict(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/attempts",
        params={"source_verdict": "SAFE", "judge_verdict": "THREAT"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["source_verdict"] == "SAFE"
    assert body["items"][0]["judge_verdict"] == "THREAT"


def test_results_are_filterable_by_input_type_and_metadata(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    response = client.get(
        "/results/attempts",
        params={
            "input_type": "agent",
            "category": "SAFETY",
            "severity": "HIGH",
            "technique": "PERSONA",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["input_type"] == "agent"
    assert body["items"][0]["category"] == "SAFETY"
    assert body["items"][0]["severity"] == "HIGH"
    assert body["items"][0]["technique"] == ["PERSONA", "ROLEPLAY"]


def test_results_are_filterable_by_context_and_output_text(
    client: TestClient, db_session: Session
) -> None:
    _dataset_with_results(db_session)

    context_response = client.get("/results/attempts", params={"q": "prompt 2"})

    assert context_response.status_code == 200
    context_body = context_response.json()
    assert context_body["total"] == 1
    assert context_body["items"][0]["source_prompt"] == "agent prompt 2"

    output_response = client.get(
        "/results/attempts",
        params={"source_output_contains": "static output"},
    )

    assert output_response.status_code == 200
    output_body = output_response.json()
    assert output_body["total"] == 1
    assert output_body["items"][0]["source_output"] == "static output"


def test_results_pagination(client: TestClient, db_session: Session) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/attempts", params={"limit": 1, "offset": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1


def test_agent_stream_timeline_is_ordered_by_attempt_index(
    client: TestClient, db_session: Session
) -> None:
    _, streams, _ = _dataset_with_results(db_session)
    agent_stream = streams[0]

    response = client.get(f"/results/streams/{agent_stream.id}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert body["stream_id"] == agent_stream.id
    assert body["input_type"] == "agent"
    assert [attempt["attempt_index"] for attempt in body["attempts"]] == [1, 2]


def test_automated_triage_summary_counts_results(client: TestClient, db_session: Session) -> None:
    _dataset_with_results(db_session)

    response = client.get("/results/triage-summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_streams"] == 2
    assert body["total_attempts"] == 3
    assert body["processed_attempts"] == 3
    assert body["remaining_attempts"] == 0
    assert body["errors"] == 1
    assert body["agreements"] == 0
    assert body["disagreements"] == 2
    assert body["source_stricter_than_judge"] == 1
    assert body["judge_stricter_than_source"] == 1
    assert body["uncertain"] == 0
    assert body["review_required"] == 0
    assert body["agent_streams"] == 1
    assert body["static_streams"] == 1
    assert body["average_attempts_per_stream"] == 1.5
