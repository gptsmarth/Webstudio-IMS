"""Allow inventory cascade on product model delete (SET NULL refs).

Revision ID: 0050_model_delete_cascade_fks
Revises: 0049_tally_guid_watermark

Notifications and Tally processed lines previously RESTRICT-blocked inventory
deletion. Align them with sales/audit (ON DELETE SET NULL) so product model
delete can cascade-clear inventory while preserving sales history snapshots.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050_model_delete_cascade_fks"
down_revision: str | None = "0049_tally_guid_watermark"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.drop_constraint(
        "fk_notifications_inventory_item",
        "notifications",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_notifications_inventory_item",
        "notifications",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_tally_processed_invoice_line_inventory",
        "tally_processed_invoice_line",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_tally_processed_invoice_line_inventory",
        "tally_processed_invoice_line",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tally_processed_invoice_line_inventory",
        "tally_processed_invoice_line",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_tally_processed_invoice_line_inventory",
        "tally_processed_invoice_line",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )

    op.drop_constraint(
        "fk_notifications_inventory_item",
        "notifications",
        schema=SCHEMA,
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_notifications_inventory_item",
        "notifications",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
