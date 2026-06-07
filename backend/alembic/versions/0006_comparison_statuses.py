"""Add comparison statuses.

Revision ID: 0006_comparison_statuses
Revises: 0005_evaluation_jobs
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_comparison_statuses"
down_revision: str | None = "0005_evaluation_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "judge_results",
        sa.Column("comparison_status", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "evaluation_errors",
        sa.Column("comparison_status", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_judge_results_comparison_status", "judge_results", ["comparison_status"])
    op.create_index(
        "ix_evaluation_errors_comparison_status", "evaluation_errors", ["comparison_status"]
    )


def downgrade() -> None:
    op.drop_index("ix_evaluation_errors_comparison_status", table_name="evaluation_errors")
    op.drop_index("ix_judge_results_comparison_status", table_name="judge_results")
    op.drop_column("evaluation_errors", "comparison_status")
    op.drop_column("judge_results", "comparison_status")
