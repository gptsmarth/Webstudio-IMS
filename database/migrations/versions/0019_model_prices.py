"""Move purchase_price and selling_price from inventory_items to product_models."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_model_prices"
down_revision: str | None = "0018_inventory_prices"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "product_models",
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("selling_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )

    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.product_models pm
            SET
                selling_price = COALESCE(pm.selling_price, sub.selling_price),
                purchase_price = COALESCE(pm.purchase_price, sub.purchase_price)
            FROM (
                SELECT
                    product_model_id,
                    MAX(selling_price) AS selling_price,
                    MAX(purchase_price) AS purchase_price
                FROM {SCHEMA}.inventory_items
                WHERE selling_price IS NOT NULL OR purchase_price IS NOT NULL
                GROUP BY product_model_id
            ) sub
            WHERE pm.id = sub.product_model_id
            """
        )
    )

    op.drop_column("inventory_items", "selling_price", schema=SCHEMA)
    op.drop_column("inventory_items", "purchase_price", schema=SCHEMA)


def downgrade() -> None:
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
    op.drop_column("product_models", "selling_price", schema=SCHEMA)
    op.drop_column("product_models", "purchase_price", schema=SCHEMA)
