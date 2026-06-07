"""Create human reviews.

Revision ID: 0007_human_reviews
Revises: 0006_comparison_statuses
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_human_reviews"
down_revision: str | None = "0006_comparison_statuses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "human_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("stream_id", sa.String(length=36), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("reviewer_identity", sa.String(length=255), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"]),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"]),
        sa.ForeignKeyConstraint(["stream_id"], ["streams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", name="uq_human_reviews_attempt_id"),
    )
    op.create_index("ix_human_reviews_attempt_id", "human_reviews", ["attempt_id"])
    op.create_index("ix_human_reviews_dataset_id", "human_reviews", ["dataset_id"])
    op.create_index("ix_human_reviews_stream_id", "human_reviews", ["stream_id"])


def downgrade() -> None:
    op.drop_index("ix_human_reviews_stream_id", table_name="human_reviews")
    op.drop_index("ix_human_reviews_dataset_id", table_name="human_reviews")
    op.drop_index("ix_human_reviews_attempt_id", table_name="human_reviews")
    op.drop_table("human_reviews")
