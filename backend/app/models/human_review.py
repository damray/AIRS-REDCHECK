import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.dataset import Dataset
    from app.models.stream import Stream


class HumanReview(Base):
    __tablename__ = "human_reviews"
    __table_args__ = (UniqueConstraint("attempt_id", name="uq_human_reviews_attempt_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"), index=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    decision: Mapped[str] = mapped_column(String(50))
    reviewer_identity: Mapped[str] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="human_reviews")
    stream: Mapped["Stream"] = relationship(back_populates="human_reviews")
    attempt: Mapped["Attempt"] = relationship(back_populates="human_reviews")
