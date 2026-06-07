import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonValue

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.evaluation_job_attempt import EvaluationJobAttempt
    from app.models.portkey_gateway_profile import PortkeyGatewayProfile


class JudgeResultRecord(Base):
    __tablename__ = "judge_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"))
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    portkey_gateway_profile_id: Mapped[str] = mapped_column(
        ForeignKey("portkey_gateway_profiles.id")
    )
    job_attempt_id: Mapped[str] = mapped_column(ForeignKey("evaluation_job_attempts.id"))
    response_verdict: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)
    response_behavior: Mapped[str] = mapped_column(String(50))
    comparison_status: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    risk_category: Mapped[str] = mapped_column(String(255))
    explanation: Mapped[str] = mapped_column(Text)
    evidence_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_response: Mapped[JsonValue] = mapped_column(JSONBType)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_usage: Mapped[JsonValue | None] = mapped_column(JSONBType, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempt: Mapped["Attempt"] = relationship()
    portkey_gateway_profile: Mapped["PortkeyGatewayProfile"] = relationship()
    job_attempt: Mapped["EvaluationJobAttempt"] = relationship(back_populates="judge_results")
