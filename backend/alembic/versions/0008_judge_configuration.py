"""Create judge configuration.

Revision ID: 0008_judge_configuration
Revises: 0007_human_reviews
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_judge_configuration"
down_revision: str | None = "0007_human_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "judge_prompt_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("rubric", sa.Text(), nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_prompt_profiles_is_default", "judge_prompt_profiles", ["is_default"])
    op.create_index(
        "ix_judge_prompt_profiles_prompt_hash", "judge_prompt_profiles", ["prompt_hash"]
    )

    op.add_column(
        "portkey_gateway_profiles",
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "evaluation_jobs",
        sa.Column("judge_prompt_profile_id", sa.String(length=36), nullable=True),
    )
    op.add_column("evaluation_jobs", sa.Column("prompt_hash", sa.String(length=64), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("judge_system_prompt", sa.Text(), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("judge_rubric", sa.Text(), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("model_name", sa.String(length=255), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("routing_mode", sa.String(length=50), nullable=True))
    op.add_column(
        "evaluation_jobs", sa.Column("provider_slug", sa.String(length=255), nullable=True)
    )
    op.add_column("evaluation_jobs", sa.Column("config_id", sa.String(length=255), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("timeout_seconds", sa.Integer(), nullable=True))
    op.add_column("evaluation_jobs", sa.Column("temperature", sa.Float(), nullable=True))
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.create_foreign_key(
            "fk_evaluation_jobs_judge_prompt_profile_id",
            "judge_prompt_profiles",
            ["judge_prompt_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("evaluation_jobs") as batch_op:
        batch_op.drop_constraint(
            "fk_evaluation_jobs_judge_prompt_profile_id",
            type_="foreignkey",
        )
    op.drop_column("evaluation_jobs", "temperature")
    op.drop_column("evaluation_jobs", "timeout_seconds")
    op.drop_column("evaluation_jobs", "config_id")
    op.drop_column("evaluation_jobs", "provider_slug")
    op.drop_column("evaluation_jobs", "routing_mode")
    op.drop_column("evaluation_jobs", "model_name")
    op.drop_column("evaluation_jobs", "judge_rubric")
    op.drop_column("evaluation_jobs", "judge_system_prompt")
    op.drop_column("evaluation_jobs", "prompt_hash")
    op.drop_column("evaluation_jobs", "judge_prompt_profile_id")
    op.drop_column("portkey_gateway_profiles", "temperature")
    op.drop_index("ix_judge_prompt_profiles_prompt_hash", table_name="judge_prompt_profiles")
    op.drop_index("ix_judge_prompt_profiles_is_default", table_name="judge_prompt_profiles")
    op.drop_table("judge_prompt_profiles")
