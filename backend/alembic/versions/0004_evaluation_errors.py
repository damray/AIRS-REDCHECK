"""Create evaluation errors.

Revision ID: 0004_evaluation_errors
Revises: 0003_portkey_gateway_profiles
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_evaluation_errors"
down_revision: str | None = "0003_portkey_gateway_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "evaluation_errors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("stream_id", sa.String(length=36), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column(
            "portkey_gateway_profile_id",
            sa.String(length=36),
            sa.ForeignKey("portkey_gateway_profiles.id"),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_response", json_type(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evaluation_errors_dataset_id", "evaluation_errors", ["dataset_id"])
    op.create_index("ix_evaluation_errors_attempt_id", "evaluation_errors", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_errors_attempt_id", table_name="evaluation_errors")
    op.drop_index("ix_evaluation_errors_dataset_id", table_name="evaluation_errors")
    op.drop_table("evaluation_errors")
