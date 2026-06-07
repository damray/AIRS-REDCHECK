import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.types import JSONBType, JsonValue

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.dataset import Dataset
    from app.models.portkey_gateway_profile import PortkeyGatewayProfile
    from app.models.stream import Stream


class EvaluationError(Base):
    __tablename__ = "evaluation_errors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    stream_id: Mapped[str] = mapped_column(ForeignKey("streams.id"))
    attempt_id: Mapped[str] = mapped_column(ForeignKey("attempts.id"), index=True)
    portkey_gateway_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("portkey_gateway_profiles.id"), nullable=True
    )
    error_code: Mapped[str] = mapped_column(String(100))
    comparison_status: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    message: Mapped[str] = mapped_column(Text)
    raw_response: Mapped[JsonValue | None] = mapped_column(JSONBType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    dataset: Mapped["Dataset"] = relationship(back_populates="evaluation_errors")
    stream: Mapped["Stream"] = relationship(back_populates="evaluation_errors")
    attempt: Mapped["Attempt"] = relationship(back_populates="evaluation_errors")
    portkey_gateway_profile: Mapped["PortkeyGatewayProfile | None"] = relationship()
