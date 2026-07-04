"""Per-unit purchase price on inventory items and sale snapshots."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043_item_purchase_price"
down_revision: str | None = "0042_deployment_monitoring"
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
        "sales",
        sa.Column("snapshot_purchase_price", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("sales", "snapshot_purchase_price", schema=SCHEMA)
    op.drop_column("inventory_items", "purchase_price", schema=SCHEMA)
