"""Create normalized import model.

Revision ID: 0001_normalized_import_model
Revises:
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_normalized_import_model"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("source_content_type", sa.String(length=100), nullable=False),
        sa.Column("detected_format", sa.String(length=50), nullable=False),
        sa.Column("parser_version", sa.String(length=50), nullable=False),
        sa.Column("raw_payload", json_type(), nullable=False),
        sa.Column("import_status", sa.String(length=50), nullable=False),
        sa.Column("stream_count", sa.Integer(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "streams",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("external_stream_id", sa.String(length=255), nullable=True),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("stream_threat_raw", sa.Text(), nullable=True),
        sa.Column("stream_threat_normalized", sa.String(length=50), nullable=True),
        sa.Column("raw_payload", json_type(), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("stream_id", sa.String(length=36), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("attempt_index", sa.Integer(), nullable=False),
        sa.Column("source_prompt", sa.Text(), nullable=False),
        sa.Column("source_output", sa.Text(), nullable=False),
        sa.Column("source_threat_raw", sa.Text(), nullable=False),
        sa.Column("source_threat_normalized", sa.String(length=50), nullable=True),
        sa.Column("source_score_raw", json_type(), nullable=True),
        sa.Column("source_reasoning", sa.Text(), nullable=True),
        sa.Column("raw_payload", json_type(), nullable=False),
        sa.Column("metadata", json_type(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "import_errors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("stream_id", sa.String(length=36), sa.ForeignKey("streams.id"), nullable=True),
        sa.Column("record_index", sa.Integer(), nullable=True),
        sa.Column("iteration_key", sa.String(length=100), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_payload", json_type(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_streams_dataset_id", "streams", ["dataset_id"])
    op.create_index("ix_attempts_dataset_id", "attempts", ["dataset_id"])
    op.create_index("ix_attempts_stream_id", "attempts", ["stream_id"])
    op.create_index("ix_import_errors_dataset_id", "import_errors", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_import_errors_dataset_id", table_name="import_errors")
    op.drop_index("ix_attempts_stream_id", table_name="attempts")
    op.drop_index("ix_attempts_dataset_id", table_name="attempts")
    op.drop_index("ix_streams_dataset_id", table_name="streams")
    op.drop_table("import_errors")
    op.drop_table("attempts")
    op.drop_table("streams")
    op.drop_table("datasets")
