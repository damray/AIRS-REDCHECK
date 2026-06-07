"""Create mapping profiles.

Revision ID: 0002_mapping_profiles
Revises: 0001_normalized_import_model
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_mapping_profiles"
down_revision: str | None = "0001_normalized_import_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "mapping_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("prompt_column", sa.String(length=255), nullable=False),
        sa.Column("output_column", sa.String(length=255), nullable=False),
        sa.Column("source_threat_column", sa.String(length=255), nullable=False),
        sa.Column("optional_field_columns", json_type(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.add_column(sa.Column("mapping_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_datasets_mapping_profile_id",
            "mapping_profiles",
            ["mapping_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_constraint("fk_datasets_mapping_profile_id", type_="foreignkey")
        batch_op.drop_column("mapping_profile_id")
    op.drop_table("mapping_profiles")
