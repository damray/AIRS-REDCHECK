import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonValue


class ImportErrorRecord(Base):
    __tablename__ = "import_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    stream_id: Mapped[str | None] = mapped_column(ForeignKey("streams.id"), nullable=True)
    record_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iteration_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    raw_payload: Mapped[JsonValue | None] = mapped_column(JSONBType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset = relationship("Dataset", back_populates="import_errors")
