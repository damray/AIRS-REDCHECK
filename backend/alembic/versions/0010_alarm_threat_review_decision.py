"""Rename ambiguous review decisions to alarm threat.

Revision ID: 0010_alarm_threat_reviews
Revises: 0009_project_workspaces
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010_alarm_threat_reviews"
down_revision: str | None = "0009_project_workspaces"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text("update human_reviews set decision = 'ALARM_THREAT' where decision = 'AMBIGUOUS'")
    )


def downgrade() -> None:
    op.execute(
        sa.text("update human_reviews set decision = 'AMBIGUOUS' where decision = 'ALARM_THREAT'")
    )
