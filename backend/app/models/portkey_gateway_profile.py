import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.types import JSONBType, JsonDict


class PortkeyGatewayProfile(Base):
    __tablename__ = "portkey_gateway_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_name: Mapped[str] = mapped_column(String(255))
    gateway_base_url: Mapped[str] = mapped_column(String(500))
    portkey_api_key: Mapped[str] = mapped_column(Text)
    routing_mode: Mapped[str] = mapped_column(String(50))
    provider_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    judge_model: Mapped[str] = mapped_column(String(255))
    temperature: Mapped[float] = mapped_column(Float, default=0.0)
    legacy_virtual_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    metadata_tags: Mapped[JsonDict] = mapped_column(JSONBType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
