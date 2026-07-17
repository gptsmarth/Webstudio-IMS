"""EAN-as-serial mode: per-brand duplicate-serial opt-in (additive, safe).

Revision ID: 0053_ean_as_serial
Revises: 0052_purchase_ignored_status

Adds:
  * brands.allow_duplicate_serials (bool, default false) — opt-in flag so an
    accessory brand can treat the EAN as the serial (many units share it).
  * inventory_items.serial_is_shared (bool, default false) — per-row flag,
    derived from the brand at creation, marking a unit as part of an EAN pool.

Changes the serial uniqueness guarantee from a plain UNIQUE constraint to a
PARTIAL unique index that only enforces uniqueness WHERE serial_is_shared =
false. This keeps every existing brand and unit exactly as before (all rows
default to serial_is_shared = false, so they stay globally unique), while
allowing opted-in EAN brands to share a serial value.

Purely additive for existing data — no row is rewritten and no existing serial
loses its uniqueness guarantee.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0053_ean_as_serial"
down_revision: str | None = "0052_purchase_ignored_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"
UNIQUE_CONSTRAINT = "uq_inventory_items_serial_number"
PARTIAL_INDEX = "uq_inventory_items_serial_number_not_shared"


def upgrade() -> None:
    op.add_column(
        "brands",
        sa.Column(
            "allow_duplicate_serials",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=SCHEMA,
    )
    op.add_column(
        "inventory_items",
        sa.Column(
            "serial_is_shared",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        schema=SCHEMA,
    )

    # Replace the blanket UNIQUE(serial_number) with a partial unique index so
    # uniqueness is enforced only for normal (non-shared) units. Kept
    # case-sensitive to exactly match the original UNIQUE(serial_number)
    # constraint — existing data already satisfies it, so this cannot fail on
    # current rows (the app-level guard remains case-insensitive as before).
    op.drop_constraint(
        UNIQUE_CONSTRAINT,
        "inventory_items",
        schema=SCHEMA,
        type_="unique",
    )
    op.execute(sa.text(f"""
            CREATE UNIQUE INDEX {PARTIAL_INDEX}
            ON {SCHEMA}.inventory_items (serial_number)
            WHERE serial_is_shared = false
            """))


def downgrade() -> None:
    # Restore the original blanket unique constraint. This can only succeed if no
    # shared-serial duplicates exist; that is acceptable for a dev-only downgrade.
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.{PARTIAL_INDEX}")
    op.create_unique_constraint(
        UNIQUE_CONSTRAINT,
        "inventory_items",
        ["serial_number"],
        schema=SCHEMA,
    )
    op.drop_column("inventory_items", "serial_is_shared", schema=SCHEMA)
    op.drop_column("brands", "allow_duplicate_serials", schema=SCHEMA)
