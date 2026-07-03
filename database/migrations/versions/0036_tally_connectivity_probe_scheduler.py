"""Persisted scheduler key for Tally connectivity background probe."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_tally_probe_scheduler"
down_revision: str | None = "0035_scheduler_runtime_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.scheduler_runtime_state (scheduler_key, interval_seconds)
            VALUES ('tally_connectivity_probe', 120)
            ON CONFLICT (scheduler_key) DO NOTHING
            """,
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.scheduler_runtime_state WHERE scheduler_key = 'tally_connectivity_probe'",
        ),
    )
