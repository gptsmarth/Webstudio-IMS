"""Add purchase_price and selling_price to inventory_items."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_inventory_prices"
down_revision: str | None = "0017_sale_amount"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "inventory_items",
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "inventory_items",
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("inventory_items", "selling_price", schema=SCHEMA)
    op.drop_column("inventory_items", "purchase_price", schema=SCHEMA)
