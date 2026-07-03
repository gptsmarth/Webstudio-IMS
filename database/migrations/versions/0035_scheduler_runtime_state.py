"""Scheduler runtime state — persisted across business-hours power cycles."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0035_scheduler_runtime_state"
down_revision: str | None = "0034_tally_incremental_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

SCHEDULER_KEYS = (
    "tally_sync",
    "backup",
    "audit_retention",
    "notification_delivery",
    "maintenance",
)


def upgrade() -> None:
    op.create_table(
        "scheduler_runtime_state",
        sa.Column("scheduler_key", sa.String(length=64), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(length=32), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("state_json", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("scheduler_key", name="pk_scheduler_runtime_state"),
        schema=SCHEMA,
    )

    seed = sa.table(
        "scheduler_runtime_state",
        sa.column("scheduler_key", sa.String),
        sa.column("interval_seconds", sa.Integer),
        schema=SCHEMA,
    )
    op.bulk_insert(
        seed,
        [
            {"scheduler_key": "tally_sync", "interval_seconds": 300},
            {"scheduler_key": "backup", "interval_seconds": 900},
            {"scheduler_key": "audit_retention", "interval_seconds": 86_400},
            {"scheduler_key": "notification_delivery", "interval_seconds": 300},
            {"scheduler_key": "maintenance", "interval_seconds": 3600},
        ],
    )


def downgrade() -> None:
    op.drop_table("scheduler_runtime_state", schema=SCHEMA)
