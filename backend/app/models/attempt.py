import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonDict, JsonValue

if TYPE_CHECKING:
    from app.models.dataset import Dataset
    from app.models.evaluation_error import EvaluationError
    from app.models.human_review import HumanReview
    from app.models.stream import Stream


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"), index=True)
    attempt_index: Mapped[int] = mapped_column(Integer)
    source_prompt: Mapped[str] = mapped_column(Text)
    source_output: Mapped[str] = mapped_column(Text)
    source_threat_raw: Mapped[str] = mapped_column(Text)
    source_threat_normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_score_raw: Mapped[JsonValue | None] = mapped_column(JSONBType, nullable=True)
    source_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[JsonValue] = mapped_column(JSONBType)
    attempt_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONBType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="attempts")
    stream: Mapped["Stream"] = relationship(back_populates="attempts")
    evaluation_errors: Mapped[list["EvaluationError"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )
    human_reviews: Mapped[list["HumanReview"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )
