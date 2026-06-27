"""Add inventory archive and optional date fields for Sprint 2A."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_inventory_sprint_2a"
down_revision: str | None = "0009_main_admin_recovery_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema=SCHEMA,
    )
    op.add_column(
        "inventory_items",
        sa.Column("purchase_date", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "inventory_items",
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_is_archived",
        "inventory_items",
        ["is_archived"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_purchase_date",
        "inventory_items",
        ["purchase_date"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_warranty_expiry",
        "inventory_items",
        ["warranty_expiry"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_inventory_items_warranty_expiry", table_name="inventory_items", schema=SCHEMA)
    op.drop_index("ix_inventory_items_purchase_date", table_name="inventory_items", schema=SCHEMA)
    op.drop_index("ix_inventory_items_is_archived", table_name="inventory_items", schema=SCHEMA)
    op.drop_column("inventory_items", "warranty_expiry", schema=SCHEMA)
    op.drop_column("inventory_items", "purchase_date", schema=SCHEMA)
    op.drop_column("inventory_items", "is_archived", schema=SCHEMA)
