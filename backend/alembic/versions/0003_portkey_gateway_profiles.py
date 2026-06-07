"""Create Portkey gateway profiles.

Revision ID: 0003_portkey_gateway_profiles
Revises: 0002_mapping_profiles
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_portkey_gateway_profiles"
down_revision: str | None = "0002_mapping_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "portkey_gateway_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("profile_name", sa.String(length=255), nullable=False),
        sa.Column("gateway_base_url", sa.String(length=500), nullable=False),
        sa.Column("portkey_api_key", sa.Text(), nullable=False),
        sa.Column("routing_mode", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=255), nullable=True),
        sa.Column("config_id", sa.String(length=255), nullable=True),
        sa.Column("judge_model", sa.String(length=255), nullable=False),
        sa.Column("legacy_virtual_key", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("metadata_tags", json_type(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("portkey_gateway_profiles")
