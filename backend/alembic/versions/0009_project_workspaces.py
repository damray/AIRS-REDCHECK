"""Add project workspaces.

Revision ID: 0009_project_workspaces
Revises: 0008_judge_configuration
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_project_workspaces"
down_revision: str | None = "0008_judge_configuration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column("datasets", sa.Column("project_id", sa.String(length=36), nullable=True))
    op.add_column("datasets", sa.Column("scan_name", sa.String(length=255), nullable=True))

    connection = op.get_bind()
    existing_count = connection.execute(sa.text("select count(*) from datasets")).scalar_one()
    if existing_count:
        default_project_id = "00000000-0000-0000-0000-000000000009"
        connection.execute(
            sa.text("insert into projects (id, name, is_archived) values (:id, :name, false)"),
            {"id": default_project_id, "name": "Imported scans"},
        )
        connection.execute(
            sa.text(
                "update datasets "
                "set project_id = :project_id, "
                "scan_name = coalesce(name, source_filename, id)"
            ),
            {"project_id": default_project_id},
        )

    with op.batch_alter_table("datasets") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("scan_name", existing_type=sa.String(length=255), nullable=False)
        batch_op.create_foreign_key(
            "fk_datasets_project_id",
            "projects",
            ["project_id"],
            ["id"],
        )
        batch_op.create_index("ix_datasets_project_id", ["project_id"])


def downgrade() -> None:
    with op.batch_alter_table("datasets") as batch_op:
        batch_op.drop_index("ix_datasets_project_id")
        batch_op.drop_constraint("fk_datasets_project_id", type_="foreignkey")
        batch_op.drop_column("scan_name")
        batch_op.drop_column("project_id")
    op.drop_table("projects")
