"""Purchase Import: add 'ignored' status (additive).

Revision ID: 0052_purchase_ignored_status
Revises: 0051_purchase_import

Adds the value 'ignored' to webstudio.tally_purchase_status so a fetched
purchase voucher can be dismissed from the review queue. This is a tombstone
state: the row is retained (hidden from the default queue) so the same Tally
voucher is not re-fetched into the queue on the next sync.

Purely additive — no existing row or column is changed.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0052_purchase_ignored_status"
down_revision: str | None = "0051_purchase_import"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    # PostgreSQL 12+ permits ADD VALUE inside a transaction as long as the new
    # value is not used in the same transaction (it is not here).
    op.execute(f"ALTER TYPE {SCHEMA}.tally_purchase_status ADD VALUE IF NOT EXISTS 'ignored'")


def downgrade() -> None:
    # PostgreSQL cannot drop a single enum value. Removing 'ignored' would
    # require recreating the type and rewriting the column; intentionally a
    # no-op so downgrade never destroys queue rows.
    pass
