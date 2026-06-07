import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonValue

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.dataset import Dataset
    from app.models.evaluation_job import EvaluationJob
    from app.models.judge_result import JudgeResultRecord
    from app.models.stream import Stream


class EvaluationJobAttempt(Base):
    __tablename__ = "evaluation_job_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("evaluation_jobs.id"), index=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=0)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[JsonValue | None] = mapped_column(JSONBType, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["EvaluationJob"] = relationship(back_populates="job_attempts")
    dataset: Mapped["Dataset"] = relationship()
    stream: Mapped["Stream"] = relationship()
    attempt: Mapped["Attempt"] = relationship()
    judge_results: Mapped[list["JudgeResultRecord"]] = relationship(back_populates="job_attempt")
