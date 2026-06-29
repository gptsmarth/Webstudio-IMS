"""Backup administration — archive flag on backup runs."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_backup_administration"
down_revision: str | None = "0023_restore_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "backup_runs",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_backup_runs_is_archived",
        "backup_runs",
        ["is_archived"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_backup_runs_is_archived", table_name="backup_runs", schema=SCHEMA)
    op.drop_column("backup_runs", "is_archived", schema=SCHEMA)
