from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Attempt,
    EvaluationJob,
    EvaluationJobAttempt,
    JudgePromptProfile,
    PortkeyGatewayProfile,
)
from app.services.judge.prompt_profiles import ensure_default_prompt_profile

TERMINAL_ATTEMPT_STATUSES = {"COMPLETED", "FAILED"}


class EvaluationJobServiceError(Exception):
    pass


class EvaluationJobService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_job(
        self,
        dataset_id: str,
        portkey_gateway_profile_id: str,
        retry_limit: int,
        judge_prompt_profile_id: str | None = None,
        attempt_ids: list[str] | None = None,
    ) -> EvaluationJob:
        profile = self.session.get(PortkeyGatewayProfile, portkey_gateway_profile_id)
        if profile is None:
            raise EvaluationJobServiceError("Portkey gateway profile not found.")
        prompt_profile = (
            ensure_default_prompt_profile(self.session)
            if judge_prompt_profile_id is None
            else self.session.get(JudgePromptProfile, judge_prompt_profile_id)
        )
        if prompt_profile is None:
            raise EvaluationJobServiceError("Judge prompt profile not found.")

        attempts_query = select(Attempt).where(Attempt.dataset_id == dataset_id)
        if attempt_ids is not None:
            attempts_query = attempts_query.where(Attempt.id.in_(attempt_ids))
        attempts = list(
            self.session.execute(attempts_query.order_by(Attempt.created_at, Attempt.id)).scalars()
        )
        if not attempts:
            raise EvaluationJobServiceError("No attempts found for evaluation job.")

        found_ids = {attempt.id for attempt in attempts}
        if attempt_ids is not None:
            missing_ids = sorted(set(attempt_ids) - found_ids)
            if missing_ids:
                raise EvaluationJobServiceError(
                    f"Attempt ids not found in dataset: {', '.join(missing_ids)}."
                )

        job = EvaluationJob(
            dataset_id=dataset_id,
            portkey_gateway_profile_id=portkey_gateway_profile_id,
            judge_prompt_profile_id=prompt_profile.id,
            prompt_hash=prompt_profile.prompt_hash,
            judge_system_prompt=prompt_profile.system_prompt,
            judge_rubric=prompt_profile.rubric,
            model_name=profile.judge_model,
            routing_mode=profile.routing_mode,
            provider_slug=profile.provider_slug,
            config_id=profile.config_id,
            timeout_seconds=profile.timeout_seconds,
            temperature=profile.temperature,
            status="PENDING",
            retry_limit=retry_limit,
            total_attempts=len(attempts),
            processed_attempts=0,
            succeeded_attempts=0,
            failed_attempts=0,
        )
        self.session.add(job)
        self.session.flush()

        for attempt in attempts:
            self.session.add(
                EvaluationJobAttempt(
                    job_id=job.id,
                    dataset_id=attempt.dataset_id,
                    stream_id=attempt.stream_id,
                    attempt_id=attempt.id,
                    status="PENDING",
                    retry_count=0,
                    max_retries=retry_limit,
                )
            )

        self.session.commit()
        self.session.refresh(job)
        return job

    def retry_failed_attempts(
        self, job_id: str, attempt_ids: list[str] | None = None
    ) -> EvaluationJob:
        job = self.session.get(EvaluationJob, job_id)
        if job is None:
            raise EvaluationJobServiceError("Evaluation job not found.")

        failed_query = select(EvaluationJobAttempt).where(
            EvaluationJobAttempt.job_id == job_id,
            EvaluationJobAttempt.status == "FAILED",
        )
        if attempt_ids is not None:
            failed_query = failed_query.where(EvaluationJobAttempt.attempt_id.in_(attempt_ids))
        failed_attempts = list(self.session.execute(failed_query).scalars())
        if not failed_attempts:
            raise EvaluationJobServiceError("No failed attempts found for retry.")

        for job_attempt in failed_attempts:
            job_attempt.status = "RETRYING"
            job_attempt.last_error_code = None
            job_attempt.last_error_message = None
            job_attempt.started_at = None
            job_attempt.completed_at = None

        job.status = "RETRYING"
        job.completed_at = None
        self.recalculate_progress(job)
        self.session.commit()
        self.session.refresh(job)
        return job

    def recalculate_progress(self, job: EvaluationJob) -> None:
        self.session.flush()
        count_rows = self.session.execute(
            select(EvaluationJobAttempt.status, func.count(EvaluationJobAttempt.id))
            .where(EvaluationJobAttempt.job_id == job.id)
            .group_by(EvaluationJobAttempt.status)
        ).all()
        counts: dict[str, int] = {status: int(count) for status, count in count_rows}
        completed = int(counts.get("COMPLETED", 0))
        failed = int(counts.get("FAILED", 0))
        job.succeeded_attempts = completed
        job.failed_attempts = failed
        job.processed_attempts = completed + failed
        non_terminal = job.total_attempts - job.processed_attempts
        if non_terminal > 0:
            if job.status not in {"RUNNING", "RETRYING"}:
                job.status = "PENDING"
            return
        if job.processed_attempts == job.total_attempts:
            job.status = "COMPLETED" if failed == 0 else "FAILED"
            job.completed_at = datetime.now(UTC)
