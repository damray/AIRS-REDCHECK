import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonValue

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.evaluation_error import EvaluationError
    from app.models.evaluation_job import EvaluationJob
    from app.models.human_review import HumanReview
    from app.models.import_error import ImportErrorRecord
    from app.models.mapping_profile import MappingProfile
    from app.models.stream import Stream


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_content_type: Mapped[str] = mapped_column(String(100))
    mapping_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("mapping_profiles.id"), nullable=True
    )
    detected_format: Mapped[str] = mapped_column(String(50))
    parser_version: Mapped[str] = mapped_column(String(50))
    raw_payload: Mapped[JsonValue] = mapped_column(JSONBType)
    import_status: Mapped[str] = mapped_column(String(50))
    stream_count: Mapped[int] = mapped_column(Integer, default=0)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    streams: Mapped[list["Stream"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    import_errors: Mapped[list["ImportErrorRecord"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    evaluation_errors: Mapped[list["EvaluationError"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    evaluation_jobs: Mapped[list["EvaluationJob"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    human_reviews: Mapped[list["HumanReview"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )
    mapping_profile: Mapped["MappingProfile | None"] = relationship(back_populates="datasets")
