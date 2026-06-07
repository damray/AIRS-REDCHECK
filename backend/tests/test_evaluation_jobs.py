import logging
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.models import (
    Attempt,
    Dataset,
    EvaluationError,
    EvaluationJob,
    JudgePromptProfile,
    JudgeResultRecord,
    PortkeyGatewayProfile,
    Stream,
)
from app.services.evaluation_jobs import EvaluationJobService
from app.services.judge.prompt_profiles import prompt_hash
from app.services.judge.schemas import (
    JudgeAdapterError,
    JudgeAdapterResponse,
    JudgeRequest,
    JudgeResult,
)
from app.services.sanitization import NUL_REPLACEMENT
from app.workers.evaluation_worker import EvaluationWorker


class SuccessfulAdapter:
    def __init__(self) -> None:
        self.requests: list[JudgeRequest] = []
        self.profiles: list[object] = []

    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        assert isinstance(request, JudgeRequest)
        self.profiles.append(profile)
        self.requests.append(request)
        return JudgeAdapterResponse(
            result=JudgeResult(
                response_verdict="SAFE",
                confidence=0.8,
                response_behavior="SAFE_REFUSAL",
                risk_category="SAFETY",
                explanation="The model refused.",
            ),
            raw_response={
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"total_tokens": 10},
                "cost": 0.01,
            },
            latency_ms=12,
            token_usage={"total_tokens": 10},
            cost=0.01,
        )


class TemporaryFailThenSuccessAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        self.calls += 1
        if self.calls == 1:
            raise JudgeAdapterError("judge_gateway_timeout", "timeout")
        return SuccessfulAdapter().evaluate(profile, request)


class UncertainAdapter:
    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        return JudgeAdapterResponse(
            result=JudgeResult(
                response_verdict="UNCERTAIN",
                confidence=0.4,
                response_behavior="AMBIGUOUS",
                risk_category="SAFETY",
                explanation="The output needs review.",
            ),
            raw_response={"choices": [{"message": {"content": "{}"}}]},
        )


class AlwaysInvalidAdapter:
    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        raise JudgeAdapterError(
            "invalid_judge_response", "invalid", raw_response={"bad": "payload"}
        )


class NulTextAdapter:
    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        return JudgeAdapterResponse(
            result=JudgeResult(
                response_verdict="SAFE",
                confidence=0.8,
                response_behavior="SAFE_REFUSAL",
                risk_category="SAFETY\x00CATEGORY",
                explanation="The model refused.\x00",
                evidence_excerpt="I cannot help.\x00",
            ),
            raw_response={
                "choices": [{"message": {"content": "contains\x00nul"}}],
            },
        )


class NulErrorAdapter:
    def evaluate(self, profile: object, request: object) -> JudgeAdapterResponse:
        raise JudgeAdapterError(
            "invalid_judge_response",
            "invalid\x00message",
            raw_response={"bad": "payload\x00value"},
        )


def _dataset_graph(
    db_session: Session, attempt_count: int = 2
) -> tuple[Dataset, PortkeyGatewayProfile]:
    dataset = Dataset(
        source_content_type="application/json",
        detected_format="static_json",
        parser_version="static-json-v1",
        raw_payload=[],
        import_status="imported",
        stream_count=attempt_count,
        attempt_count=attempt_count,
        error_count=0,
    )
    profile = PortkeyGatewayProfile(
        profile_name="p",
        gateway_base_url="https://gateway.example.test",
        portkey_api_key="pk-test-secret-value",
        routing_mode="provider_slug",
        provider_slug="openai",
        config_id=None,
        judge_model="gpt-test",
        legacy_virtual_key=None,
        timeout_seconds=5,
        metadata_tags={},
    )
    db_session.add(dataset)
    db_session.add(profile)
    db_session.flush()

    for index in range(attempt_count):
        stream = Stream(
            dataset_id=dataset.id,
            input_type="agent",
            goal=f"goal {index}",
            raw_payload={"i": index},
            stream_metadata={},
        )
        db_session.add(stream)
        db_session.flush()
        db_session.add(
            Attempt(
                dataset_id=dataset.id,
                stream_id=stream.id,
                attempt_index=index,
                source_prompt=f"prompt {index}",
                source_output=f"output {index}",
                source_threat_raw="True",
                source_threat_normalized="THREAT",
                source_score_raw=99,
                source_reasoning="source reasoning must stay blind",
                raw_payload={"i": index},
                attempt_metadata={},
            )
        )
    db_session.commit()
    return dataset, profile


def _prompt_profile(db_session: Session) -> JudgePromptProfile:
    profile = JudgePromptProfile(
        name="custom prompt",
        system_prompt="Custom system prompt",
        rubric="Custom rubric",
        prompt_hash=prompt_hash("Custom system prompt", "Custom rubric"),
        is_default=True,
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def test_create_evaluation_job_persists_pending_rows_before_execution(
    client: TestClient,
    db_session: Session,
) -> None:
    dataset, profile = _dataset_graph(db_session)

    response = client.post(
        "/evaluation-jobs",
        json={
            "dataset_id": dataset.id,
            "portkey_gateway_profile_id": profile.id,
            "retry_limit": 2,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["total_attempts"] == 2
    job = db_session.get(EvaluationJob, body["id"])
    assert job is not None
    assert [attempt.status for attempt in job.job_attempts] == ["PENDING", "PENDING"]


def test_create_evaluation_job_persists_prompt_and_model_configuration_snapshot(
    client: TestClient,
    db_session: Session,
) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    profile.judge_model = "gpt-snapshot"
    profile.temperature = 0.3
    profile.timeout_seconds = 17
    prompt_profile = _prompt_profile(db_session)

    response = client.post(
        "/evaluation-jobs",
        json={
            "dataset_id": dataset.id,
            "portkey_gateway_profile_id": profile.id,
            "judge_prompt_profile_id": prompt_profile.id,
            "retry_limit": 2,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["judge_prompt_profile_id"] == prompt_profile.id
    assert body["prompt_hash"] == prompt_profile.prompt_hash
    assert body["model_name"] == "gpt-snapshot"
    assert body["temperature"] == 0.3
    assert body["timeout_seconds"] == 17
    job = db_session.get(EvaluationJob, body["id"])
    assert job is not None
    assert job.judge_system_prompt == "Custom system prompt"
    assert job.judge_rubric == "Custom rubric"


def test_status_endpoint_reports_progress(client: TestClient, db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    job_attempt = job.job_attempts[0]
    job_attempt.status = "COMPLETED"
    EvaluationJobService(db_session).recalculate_progress(job)
    db_session.commit()

    response = client.get(f"/evaluation-jobs/{job.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["processed_attempts"] == 1
    assert body["succeeded_attempts"] == 1
    assert body["job_attempts"][0]["status"] == "COMPLETED"


def test_worker_processes_pending_job_and_records_result(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    profile.judge_model = "model-before-job"
    profile.temperature = 0.4
    prompt_profile = _prompt_profile(db_session)
    job = EvaluationJobService(db_session).create_job(
        dataset.id,
        profile.id,
        retry_limit=1,
        judge_prompt_profile_id=prompt_profile.id,
    )
    profile.judge_model = "model-after-job"
    profile.temperature = 1.3
    db_session.commit()
    adapter = SuccessfulAdapter()

    processed = EvaluationWorker(db_session, adapter=adapter).process_next_job()

    assert processed is True
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.processed_attempts == 1
    result = db_session.query(JudgeResultRecord).one()
    assert result.response_verdict == "SAFE"
    assert result.comparison_status == "SOURCE_STRICTER_THAN_JUDGE"
    assert result.latency_ms == 12
    assert result.token_usage == {"total_tokens": 10}
    assert result.cost == 0.01
    request_json = adapter.requests[0].model_dump_json()
    assert adapter.requests[0].system_prompt == "Custom system prompt"
    assert adapter.requests[0].rubric == "Custom rubric"
    assert isinstance(adapter.profiles[0], PortkeyGatewayProfile)
    assert adapter.profiles[0].judge_model == "model-before-job"
    assert adapter.profiles[0].temperature == 0.4
    assert "prompt 0" in request_json
    assert "output 0" in request_json
    assert "goal 0" in request_json
    assert "source_reasoning" not in request_json
    assert "source reasoning must stay blind" not in request_json
    assert "source_score" not in request_json
    assert "source_threat" not in request_json


def test_worker_logs_progress_without_prompt_output_or_secrets(
    db_session: Session,
    caplog: Any,
) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)

    with caplog.at_level(logging.INFO, logger="app.workers.evaluation_worker"):
        EvaluationWorker(db_session, adapter=SuccessfulAdapter()).process_next_job()

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert "Claimed evaluation job" in log_text
    assert "Started evaluation attempt" in log_text
    assert "Completed evaluation attempt" in log_text
    assert "prompt 0" not in log_text
    assert "output 0" not in log_text
    assert "pk-test-secret-value" not in log_text


def test_worker_marks_uncertain_judge_result_review_required(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)

    EvaluationWorker(db_session, adapter=UncertainAdapter()).process_next_job()

    result = db_session.query(JudgeResultRecord).one()
    assert result.response_verdict == "UNCERTAIN"
    assert result.comparison_status == "REVIEW_REQUIRED"


def test_worker_sanitizes_nul_bytes_in_judge_result_text(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)

    EvaluationWorker(db_session, adapter=NulTextAdapter()).process_next_job()

    result = db_session.query(JudgeResultRecord).one()
    assert result.risk_category == f"SAFETY{NUL_REPLACEMENT}CATEGORY"
    assert result.explanation == f"The model refused.{NUL_REPLACEMENT}"
    assert result.evidence_excerpt == f"I cannot help.{NUL_REPLACEMENT}"
    assert result.raw_response == {
        "choices": [{"message": {"content": f"contains{NUL_REPLACEMENT}nul"}}]
    }


def test_worker_sanitizes_nul_bytes_in_evaluation_error_text(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=0)

    EvaluationWorker(db_session, adapter=NulErrorAdapter()).process_next_job()

    db_session.refresh(job)
    error = db_session.query(EvaluationError).one()
    assert job.job_attempts[0].last_error_message == f"invalid{NUL_REPLACEMENT}message"
    assert error.message == f"invalid{NUL_REPLACEMENT}message"
    assert error.raw_response == {"bad": f"payload{NUL_REPLACEMENT}value"}


def test_worker_recovers_running_job_after_restart(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    job.status = "RUNNING"
    job.job_attempts[0].status = "RUNNING"
    db_session.commit()

    recovered = EvaluationWorker(db_session).recover_interrupted_jobs()

    db_session.refresh(job)
    assert recovered == 1
    assert job.status == "PENDING"
    assert job.job_attempts[0].status == "PENDING"


def test_worker_tolerates_job_rows_deleted_by_dashboard_reset(
    db_session: Session,
    monkeypatch: Any,
) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    worker = EvaluationWorker(db_session)

    def stale_process(job: EvaluationJob, job_attempt: object) -> None:
        raise StaleDataError("row was deleted by reset")

    monkeypatch.setattr(worker, "_process_job_attempt", stale_process)

    assert worker.process_next_job() is True


def test_worker_retries_temporary_errors_with_limit(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    adapter = TemporaryFailThenSuccessAdapter()

    EvaluationWorker(db_session, adapter=adapter).process_next_job()

    db_session.refresh(job)
    assert adapter.calls == 2
    assert job.status == "COMPLETED"
    assert job.job_attempts[0].retry_count == 1


def test_worker_fails_after_retry_limit_and_failed_attempt_can_be_retried(
    client: TestClient,
    db_session: Session,
) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=1)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=0)

    EvaluationWorker(db_session, adapter=AlwaysInvalidAdapter()).process_next_job()

    db_session.refresh(job)
    assert job.status == "FAILED"
    assert job.failed_attempts == 1
    assert job.job_attempts[0].status == "FAILED"
    error = db_session.query(EvaluationError).one()
    assert error.comparison_status == "EVALUATION_ERROR"

    response = client.post(f"/evaluation-jobs/{job.id}/retry-failed")

    assert response.status_code == 200
    db_session.refresh(job)
    assert job.status == "RETRYING"
    assert job.job_attempts[0].status == "RETRYING"


def test_retry_failed_can_select_specific_attempts(db_session: Session) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=2)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    first, second = job.job_attempts
    first.status = "FAILED"
    second.status = "FAILED"
    db_session.commit()

    EvaluationJobService(db_session).retry_failed_attempts(job.id, attempt_ids=[first.attempt_id])

    db_session.refresh(first)
    db_session.refresh(second)
    assert first.status == "RETRYING"
    assert second.status == "FAILED"


def test_retry_failed_endpoint_can_select_specific_attempts(
    client: TestClient,
    db_session: Session,
) -> None:
    dataset, profile = _dataset_graph(db_session, attempt_count=2)
    job = EvaluationJobService(db_session).create_job(dataset.id, profile.id, retry_limit=1)
    first, second = job.job_attempts
    first.status = "FAILED"
    second.status = "FAILED"
    db_session.commit()

    response = client.post(
        f"/evaluation-jobs/{job.id}/retry-failed",
        json={"attempt_ids": [first.attempt_id]},
    )

    assert response.status_code == 200
    db_session.refresh(first)
    db_session.refresh(second)
    assert first.status == "RETRYING"
    assert second.status == "FAILED"


def test_worker_module_does_not_use_fastapi_background_tasks() -> None:
    from pathlib import Path

    worker_source = Path("app/workers/evaluation_worker.py").read_text()

    assert "BackgroundTasks" not in worker_source
    assert "fastapi" not in worker_source
