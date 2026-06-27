"""Add inventory query performance indexes for Sprint 2C."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_inventory_performance"
down_revision: str | None = "0011_sales"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            CREATE INDEX IF NOT EXISTS ix_inventory_items_serial_number_lower
            ON {SCHEMA}.inventory_items (lower(serial_number))
            """,
        ),
    )
    op.create_index(
        "ix_inventory_items_list_default",
        "inventory_items",
        ["is_archived", "status", sa.text("updated_at DESC")],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_location_status",
        "inventory_items",
        ["current_location_id", "status"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_model_status",
        "inventory_items",
        ["product_model_id", "status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_items_model_status", table_name="inventory_items", schema=SCHEMA)
    op.drop_index("ix_inventory_items_location_status", table_name="inventory_items", schema=SCHEMA)
    op.drop_index("ix_inventory_items_list_default", table_name="inventory_items", schema=SCHEMA)
    op.execute(
        sa.text(f"DROP INDEX IF EXISTS {SCHEMA}.ix_inventory_items_serial_number_lower"),
    )
