"""Disaster recovery — backup notification types and backup alerts setting."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_disaster_recovery"
down_revision: str | None = "0024_backup_administration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        sa.text(f"""
            DO $$ BEGIN
                ALTER TYPE {SCHEMA}.{enum_name} ADD VALUE IF NOT EXISTS '{value}';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """),
    )


def upgrade() -> None:
    for value in ("backup_failed", "backup_completed", "low_storage", "recovery_completed"):
        _add_enum_value("notification_type", value)


def downgrade() -> None:
    pass
