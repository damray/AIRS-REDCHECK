import logging
import time
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError, StaleDataError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import (
    EvaluationError,
    EvaluationJob,
    EvaluationJobAttempt,
    JudgeResultRecord,
    PortkeyGatewayProfile,
)
from app.services.comparison import compare_source_and_judge
from app.services.evaluation_jobs import EvaluationJobService
from app.services.judge.blind import build_blind_judge_request
from app.services.judge.portkey_adapter import PortkeyJudgeAdapter
from app.services.judge.schemas import JudgeAdapterError, JudgeAdapterResponse, JudgeRequest
from app.services.sanitization import sanitize_json_for_postgres, sanitize_text_for_postgres

TEMPORARY_ERROR_CODES = {
    "judge_gateway_timeout",
    "judge_gateway_error",
    "judge_gateway_status_error",
}

logger = logging.getLogger(__name__)


class JudgeAdapter(Protocol):
    def evaluate(
        self,
        profile: PortkeyGatewayProfile,
        request: JudgeRequest,
    ) -> JudgeAdapterResponse: ...


class EvaluationWorker:
    def __init__(self, session: Session, adapter: JudgeAdapter | None = None) -> None:
        self.session = session
        self.adapter = adapter or PortkeyJudgeAdapter()

    def recover_interrupted_jobs(self) -> int:
        jobs = list(
            self.session.execute(
                select(EvaluationJob).where(EvaluationJob.status == "RUNNING")
            ).scalars()
        )
        recovered = 0
        for job in jobs:
            running_attempts = list(
                self.session.execute(
                    select(EvaluationJobAttempt).where(
                        EvaluationJobAttempt.job_id == job.id,
                        EvaluationJobAttempt.status == "RUNNING",
                    )
                ).scalars()
            )
            for job_attempt in running_attempts:
                job_attempt.status = "PENDING"
                job_attempt.started_at = None
            job.status = "PENDING"
            job.started_at = None
            recovered += 1
        self.session.commit()
        if recovered:
            logger.info("Recovered interrupted evaluation jobs count=%s", recovered)
        return recovered

    def process_next_job(self) -> bool:
        job = self._claim_next_job()
        if job is None:
            return False

        while True:
            job_attempt = self._next_pending_attempt(job.id)
            if job_attempt is None:
                try:
                    EvaluationJobService(self.session).recalculate_progress(job)
                    self.session.commit()
                    logger.info(
                        "Finished evaluation job job_id=%s status=%s processed=%s "
                        "total=%s succeeded=%s failed=%s",
                        job.id,
                        job.status,
                        job.processed_attempts,
                        job.total_attempts,
                        job.succeeded_attempts,
                        job.failed_attempts,
                    )
                except (ObjectDeletedError, StaleDataError):
                    self.session.rollback()
                    logger.info("Evaluation job disappeared during reset job_id=%s", job.id)
                return True
            try:
                self._process_job_attempt(job, job_attempt)
            except (ObjectDeletedError, StaleDataError):
                self.session.rollback()
                logger.info(
                    "Evaluation job attempt disappeared during reset job_id=%s job_attempt_id=%s",
                    job.id,
                    job_attempt.id,
                )
                return True

    def _claim_next_job(self) -> EvaluationJob | None:
        job = self.session.execute(
            select(EvaluationJob)
            .where(EvaluationJob.status.in_(["PENDING", "RETRYING"]))
            .order_by(EvaluationJob.created_at, EvaluationJob.id)
            .limit(1)
        ).scalar_one_or_none()
        if job is None:
            return None
        job.status = "RUNNING"
        job.started_at = job.started_at or datetime.now(UTC)
        self.session.commit()
        self.session.refresh(job)
        logger.info(
            "Claimed evaluation job job_id=%s dataset_id=%s total_attempts=%s retry_limit=%s",
            job.id,
            job.dataset_id,
            job.total_attempts,
            job.retry_limit,
        )
        return job

    def _next_pending_attempt(self, job_id: str) -> EvaluationJobAttempt | None:
        return self.session.execute(
            select(EvaluationJobAttempt)
            .where(
                EvaluationJobAttempt.job_id == job_id,
                EvaluationJobAttempt.status.in_(["PENDING", "RETRYING"]),
            )
            .order_by(EvaluationJobAttempt.created_at, EvaluationJobAttempt.id)
            .limit(1)
        ).scalar_one_or_none()

    def _process_job_attempt(self, job: EvaluationJob, job_attempt: EvaluationJobAttempt) -> None:
        job_attempt.status = "RUNNING"
        job_attempt.started_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(job_attempt)
        logger.info(
            "Started evaluation attempt job_id=%s job_attempt_id=%s attempt_id=%s "
            "retry_count=%s max_retries=%s",
            job.id,
            job_attempt.id,
            job_attempt.attempt_id,
            job_attempt.retry_count,
            job_attempt.max_retries,
        )

        try:
            request = build_blind_judge_request(
                attempt=job_attempt.attempt,
                goal=job_attempt.stream.goal,
                system_prompt=job.judge_system_prompt or "",
                rubric=job.judge_rubric or "",
            )
            adapter_response = self.adapter.evaluate(self._gateway_profile_for_job(job), request)
        except JudgeAdapterError as exc:
            self._handle_adapter_error(job_attempt, exc)
            EvaluationJobService(self.session).recalculate_progress(job)
            self.session.commit()
            return

        result = adapter_response.result
        job_attempt.status = "COMPLETED"
        job_attempt.latency_ms = adapter_response.latency_ms
        job_attempt.token_usage = adapter_response.token_usage
        job_attempt.cost = adapter_response.cost
        job_attempt.completed_at = datetime.now(UTC)
        self.session.add(
            JudgeResultRecord(
                dataset_id=job_attempt.dataset_id,
                stream_id=job_attempt.stream_id,
                attempt_id=job_attempt.attempt_id,
                portkey_gateway_profile_id=job.portkey_gateway_profile_id,
                job_attempt_id=job_attempt.id,
                response_verdict=result.response_verdict,
                confidence=result.confidence,
                response_behavior=result.response_behavior,
                comparison_status=compare_source_and_judge(
                    source_verdict=job_attempt.attempt.source_threat_normalized,
                    judge_verdict=result.response_verdict,
                ),
                risk_category=sanitize_text_for_postgres(result.risk_category) or "",
                explanation=sanitize_text_for_postgres(result.explanation) or "",
                evidence_excerpt=sanitize_text_for_postgres(result.evidence_excerpt),
                raw_response=sanitize_json_for_postgres(adapter_response.raw_response),
                latency_ms=adapter_response.latency_ms,
                token_usage=adapter_response.token_usage,
                cost=adapter_response.cost,
            )
        )
        EvaluationJobService(self.session).recalculate_progress(job)
        self.session.commit()
        logger.info(
            "Completed evaluation attempt job_id=%s job_attempt_id=%s attempt_id=%s "
            "verdict=%s comparison_status=%s latency_ms=%s",
            job.id,
            job_attempt.id,
            job_attempt.attempt_id,
            result.response_verdict,
            compare_source_and_judge(
                source_verdict=job_attempt.attempt.source_threat_normalized,
                judge_verdict=result.response_verdict,
            ),
            adapter_response.latency_ms,
        )

    def _handle_adapter_error(
        self, job_attempt: EvaluationJobAttempt, exc: JudgeAdapterError
    ) -> None:
        if (
            exc.error_code in TEMPORARY_ERROR_CODES
            and job_attempt.retry_count < job_attempt.max_retries
        ):
            job_attempt.retry_count += 1
            job_attempt.status = "RETRYING"
            job_attempt.last_error_code = sanitize_text_for_postgres(exc.error_code)
            job_attempt.last_error_message = sanitize_text_for_postgres(exc.message)
            job_attempt.started_at = None
            logger.info(
                "Retrying evaluation attempt job_attempt_id=%s attempt_id=%s "
                "error_code=%s retry_count=%s max_retries=%s",
                job_attempt.id,
                job_attempt.attempt_id,
                exc.error_code,
                job_attempt.retry_count,
                job_attempt.max_retries,
            )
            return

        job_attempt.status = "FAILED"
        job_attempt.last_error_code = sanitize_text_for_postgres(exc.error_code)
        job_attempt.last_error_message = sanitize_text_for_postgres(exc.message)
        job_attempt.completed_at = datetime.now(UTC)
        self.session.add(
            EvaluationError(
                dataset_id=job_attempt.dataset_id,
                stream_id=job_attempt.stream_id,
                attempt_id=job_attempt.attempt_id,
                portkey_gateway_profile_id=job_attempt.job.portkey_gateway_profile_id,
                error_code=sanitize_text_for_postgres(exc.error_code) or "",
                comparison_status=compare_source_and_judge(
                    source_verdict=job_attempt.attempt.source_threat_normalized,
                    judge_verdict=None,
                    evaluation_error=True,
                ),
                message=sanitize_text_for_postgres(exc.message) or "",
                raw_response=sanitize_json_for_postgres(exc.raw_response),
            )
        )
        logger.info(
            "Failed evaluation attempt job_attempt_id=%s attempt_id=%s error_code=%s "
            "retry_count=%s max_retries=%s",
            job_attempt.id,
            job_attempt.attempt_id,
            exc.error_code,
            job_attempt.retry_count,
            job_attempt.max_retries,
        )

    def _gateway_profile_for_job(self, job: EvaluationJob) -> PortkeyGatewayProfile:
        source = job.portkey_gateway_profile
        return PortkeyGatewayProfile(
            profile_name=source.profile_name,
            gateway_base_url=source.gateway_base_url,
            portkey_api_key=source.portkey_api_key,
            routing_mode=job.routing_mode or source.routing_mode,
            provider_slug=job.provider_slug,
            config_id=job.config_id,
            judge_model=job.model_name or source.judge_model,
            temperature=job.temperature if job.temperature is not None else source.temperature,
            legacy_virtual_key=source.legacy_virtual_key,
            timeout_seconds=job.timeout_seconds or source.timeout_seconds,
            metadata_tags=source.metadata_tags,
        )


def run_forever() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    settings = get_settings()
    logger.info("Starting evaluation worker poll_seconds=%s", settings.worker_poll_seconds)
    with SessionLocal() as session:
        worker = EvaluationWorker(session)
        worker.recover_interrupted_jobs()
        while True:
            processed = worker.process_next_job()
            if not processed:
                time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    run_forever()
