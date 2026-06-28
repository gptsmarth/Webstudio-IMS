"""Remove warranty columns — out of scope for v1.

Revision ID: 0015_remove_warranty_columns
Revises: 0014_reference_apis_expansion
Create Date: 2026-06-27 14:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_remove_warranty_columns"
down_revision: str | None = "0014_reference_apis_expansion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.drop_index("ix_inventory_items_warranty_expiry", table_name="inventory_items", schema=SCHEMA)
    op.drop_column("inventory_items", "warranty_expiry", schema=SCHEMA)
    op.drop_column("product_models", "warranty", schema=SCHEMA)


def downgrade() -> None:
    op.add_column(
        "product_models",
        sa.Column("warranty", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "inventory_items",
        sa.Column("warranty_expiry", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_inventory_items_warranty_expiry",
        "inventory_items",
        ["warranty_expiry"],
        schema=SCHEMA,
    )
