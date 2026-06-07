import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonDict

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class MappingProfile(Base):
    __tablename__ = "mapping_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    prompt_column: Mapped[str] = mapped_column(String(255))
    output_column: Mapped[str] = mapped_column(String(255))
    source_threat_column: Mapped[str] = mapped_column(String(255))
    optional_field_columns: Mapped[JsonDict] = mapped_column(JSONBType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="mapping_profile")
