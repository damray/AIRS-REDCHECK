import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.evaluation_job import EvaluationJob


class JudgePromptProfile(Base):
    __tablename__ = "judge_prompt_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    system_prompt: Mapped[str] = mapped_column(Text)
    rubric: Mapped[str] = mapped_column(Text)
    prompt_hash: Mapped[str] = mapped_column(String(64), index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evaluation_jobs: Mapped[list["EvaluationJob"]] = relationship(back_populates="prompt_profile")
