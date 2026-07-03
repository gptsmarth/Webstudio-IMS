"""Enterprise restore engine — restore run history and rollback support."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_restore_engine"
down_revision: str | None = "0022_backup_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.create_table(
        "restore_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="local"),
        sa.Column(
            "restore_scope", sa.String(length=32), nullable=False, server_default="entire_database"
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column(
            "verification_status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("emergency_backup_filename", sa.String(length=256), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("actor_display_name", sa.String(length=128), nullable=True),
        sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("errors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_restore_runs_actor_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_restore_runs"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_restore_runs_created_at",
        "restore_runs",
        ["created_at"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_restore_runs_created_at", table_name="restore_runs", schema=SCHEMA)
    op.drop_table("restore_runs", schema=SCHEMA)
