"""Enterprise backup enhancements — restore notification types."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_backup_enterprise"
down_revision: str | None = "0025_disaster_recovery"
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
    for value in (
        "restore_started",
        "restore_completed",
        "restore_failed",
        "backup_verification_failed",
    ):
        _add_enum_value("notification_type", value)


def downgrade() -> None:
    pass
