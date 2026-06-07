import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.evaluation_job_attempt import EvaluationJobAttempt
    from app.models.judge_prompt_profile import JudgePromptProfile
    from app.models.portkey_gateway_profile import PortkeyGatewayProfile


class EvaluationJob(Base):
    __tablename__ = "evaluation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    portkey_gateway_profile_id: Mapped[str] = mapped_column(
        ForeignKey("portkey_gateway_profiles.id")
    )
    judge_prompt_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("judge_prompt_profiles.id"), nullable=True
    )
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    judge_system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    routing_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    retry_limit: Mapped[int] = mapped_column(Integer)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    processed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    succeeded_attempts: Mapped[int] = mapped_column(Integer, default=0)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="evaluation_jobs")
    portkey_gateway_profile: Mapped["PortkeyGatewayProfile"] = relationship()
    prompt_profile: Mapped["JudgePromptProfile | None"] = relationship(
        back_populates="evaluation_jobs"
    )
    job_attempts: Mapped[list["EvaluationJobAttempt"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
