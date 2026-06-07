"""Create evaluation jobs.

Revision ID: 0005_evaluation_jobs
Revises: 0004_evaluation_errors
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_evaluation_jobs"
down_revision: str | None = "0004_evaluation_errors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type() -> sa.types.TypeEngine[object]:
    return postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "evaluation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column(
            "portkey_gateway_profile_id",
            sa.String(length=36),
            sa.ForeignKey("portkey_gateway_profiles.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("retry_limit", sa.Integer(), nullable=False),
        sa.Column("total_attempts", sa.Integer(), nullable=False),
        sa.Column("processed_attempts", sa.Integer(), nullable=False),
        sa.Column("succeeded_attempts", sa.Integer(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "evaluation_job_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "job_id", sa.String(length=36), sa.ForeignKey("evaluation_jobs.id"), nullable=False
        ),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("stream_id", sa.String(length=36), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", json_type(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "judge_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("dataset_id", sa.String(length=36), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("stream_id", sa.String(length=36), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), sa.ForeignKey("attempts.id"), nullable=False),
        sa.Column(
            "portkey_gateway_profile_id",
            sa.String(length=36),
            sa.ForeignKey("portkey_gateway_profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "job_attempt_id",
            sa.String(length=36),
            sa.ForeignKey("evaluation_job_attempts.id"),
            nullable=False,
        ),
        sa.Column("response_verdict", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("response_behavior", sa.String(length=50), nullable=False),
        sa.Column("risk_category", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_excerpt", sa.Text(), nullable=True),
        sa.Column("raw_response", json_type(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", json_type(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_evaluation_jobs_dataset_id", "evaluation_jobs", ["dataset_id"])
    op.create_index("ix_evaluation_jobs_status", "evaluation_jobs", ["status"])
    op.create_index("ix_evaluation_job_attempts_job_id", "evaluation_job_attempts", ["job_id"])
    op.create_index(
        "ix_evaluation_job_attempts_attempt_id", "evaluation_job_attempts", ["attempt_id"]
    )
    op.create_index("ix_evaluation_job_attempts_status", "evaluation_job_attempts", ["status"])
    op.create_index("ix_judge_results_attempt_id", "judge_results", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_judge_results_attempt_id", table_name="judge_results")
    op.drop_index("ix_evaluation_job_attempts_status", table_name="evaluation_job_attempts")
    op.drop_index("ix_evaluation_job_attempts_attempt_id", table_name="evaluation_job_attempts")
    op.drop_index("ix_evaluation_job_attempts_job_id", table_name="evaluation_job_attempts")
    op.drop_index("ix_evaluation_jobs_status", table_name="evaluation_jobs")
    op.drop_index("ix_evaluation_jobs_dataset_id", table_name="evaluation_jobs")
    op.drop_table("judge_results")
    op.drop_table("evaluation_job_attempts")
    op.drop_table("evaluation_jobs")
