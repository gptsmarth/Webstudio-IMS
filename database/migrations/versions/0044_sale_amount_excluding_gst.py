"""Store Tally sale amounts with and without GST."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044_sale_amount_excluding_gst"
down_revision: str | None = "0043_item_purchase_price"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("sale_amount_excluding_gst", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.sales
            SET sale_amount_excluding_gst = sale_amount,
                sale_amount = ROUND((sale_amount * 1.18)::numeric, 2)
            WHERE sale_source = 'tally'
              AND sale_amount IS NOT NULL
              AND sale_amount_excluding_gst IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.sales
            SET sale_amount = sale_amount_excluding_gst
            WHERE sale_source = 'tally'
              AND sale_amount_excluding_gst IS NOT NULL
            """
        )
    )
    op.drop_column("sales", "sale_amount_excluding_gst", schema=SCHEMA)
