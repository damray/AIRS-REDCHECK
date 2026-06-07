import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonDict, JsonValue

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.dataset import Dataset
    from app.models.evaluation_error import EvaluationError
    from app.models.human_review import HumanReview


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    external_stream_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_type: Mapped[str] = mapped_column(String(20))
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    stream_threat_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    stream_threat_normalized: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_payload: Mapped[JsonValue] = mapped_column(JSONBType)
    stream_metadata: Mapped[JsonDict] = mapped_column("metadata", JSONBType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="streams")
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan"
    )
    evaluation_errors: Mapped[list["EvaluationError"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan"
    )
    human_reviews: Mapped[list["HumanReview"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan"
    )
