"""Purge archived, unsold inventory serials (one-shot cleanup).

Revision ID: 0054_purge_archived_serials
Revises: 0053_ean_as_serial

Operators previously used "Archive" as a soft-delete for incorrect serials.
Going forward those units should be hard-deleted from stock and inventory.
This migration permanently removes every inventory_item where:

  * is_archived = true
  * status != 'sold'
  * no sale row still references the unit

Sold units (and any unit with a sale reference) are intentionally left alone —
sales history must never be destroyed. Soft-delete (archive) remains available
in the API for temporary hide/restore, but previously-archived junk is cleaned
out of the production database on the next server update.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0054_purge_archived_serials"
down_revision: str | None = "0053_ean_as_serial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    # Identify the purge set once, then clear FK references and delete.
    # Sold units / sale-referenced units are excluded so sales history is safe.
    # SQL is assigned to locals first so Black 24.x and 26.x agree on formatting
    # (they disagree on `op.execute(f"""...""")` vs parenthesized multiline strings).
    select_archived = f"""
        CREATE TEMP TABLE _purge_archived_serials ON COMMIT DROP AS
        SELECT ii.id
        FROM {SCHEMA}.inventory_items AS ii
        WHERE ii.is_archived = true
          AND ii.status <> 'sold'
          AND NOT EXISTS (
              SELECT 1
              FROM {SCHEMA}.sales AS s
              WHERE s.inventory_item_id = ii.id
          )
        """
    op.execute(select_archived)

    for table in (
        "sales",
        "audit_logs",
        "notifications",
        "tally_processed_invoice_line",
        "tally_line_decision_log",
    ):
        clear_fk = f"""
            UPDATE {SCHEMA}.{table} AS t
            SET inventory_item_id = NULL
            WHERE t.inventory_item_id IN (SELECT id FROM _purge_archived_serials)
            """
        op.execute(clear_fk)

    delete_archived = f"""
        DELETE FROM {SCHEMA}.inventory_items AS ii
        WHERE ii.id IN (SELECT id FROM _purge_archived_serials)
        """
    op.execute(delete_archived)


def downgrade() -> None:
    # Irreversible data cleanup — archived serials cannot be reconstructed.
    pass
