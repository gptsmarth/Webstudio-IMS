"""Add ASUS live-price tracking columns to product_models.

Revision ID: 0057_asus_live_price
Revises: 0056_sale_gst_breakdown

Purely additive: five nullable columns on `product_models`, populated by a
background job that asks Gemini (with Google Search grounding) for a
model's current price on ASUS's own India store. `live_price` only ever
holds the last *successfully* resolved value — `live_price_checked_at`
(every attempt) is kept separate from `live_price_updated_at` (only
successful changes) so a failed refresh never erases a still-useful last
known price. Scope is ASUS only; other brands simply never populate these.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0057_asus_live_price"
down_revision: str | None = "0056_sale_gst_breakdown"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "product_models",
        sa.Column("live_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("live_price_status", sa.String(32), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("live_price_source_url", sa.String(512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("live_price_checked_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("live_price_updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("product_models", "live_price_updated_at", schema=SCHEMA)
    op.drop_column("product_models", "live_price_checked_at", schema=SCHEMA)
    op.drop_column("product_models", "live_price_source_url", schema=SCHEMA)
    op.drop_column("product_models", "live_price_status", schema=SCHEMA)
    op.drop_column("product_models", "live_price", schema=SCHEMA)
