"""Add sale cancellation fields for invoice delete / stock restore."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_sale_cancellation"
down_revision: str | None = "0045_product_accessory_category"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("cancelled_by_user_id", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sales_cancelled_at",
        "sales",
        ["cancelled_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_sales_cancelled_at", table_name="sales", schema=SCHEMA)
    op.drop_column("sales", "cancellation_reason", schema=SCHEMA)
    op.drop_column("sales", "cancelled_by_user_id", schema=SCHEMA)
    op.drop_column("sales", "cancelled_at", schema=SCHEMA)
