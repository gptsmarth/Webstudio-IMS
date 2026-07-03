"""Add columns for reference APIs expansion.

Revision ID: 0014_reference_apis_expansion
Revises: 0013_notifications
Create Date: 2026-06-28 12:20:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_reference_apis_expansion"
down_revision: str | None = "0013_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    # Add columns to brands table
    op.add_column(
        "brands", sa.Column("short_name", sa.String(length=64), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "brands", sa.Column("logo_filename", sa.String(length=256), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "brands",
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        schema=SCHEMA,
    )

    # Add columns to product_models table
    op.add_column(
        "product_models", sa.Column("display", sa.String(length=128), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "product_models",
        sa.Column("color_options", sa.String(length=256), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models", sa.Column("warranty", sa.String(length=128), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "product_models",
        sa.Column("product_image_url", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models",
        sa.Column("search_aliases", sa.String(length=1024), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "product_models", sa.Column("notes", sa.String(length=2000), nullable=True), schema=SCHEMA
    )


def downgrade() -> None:
    # Remove columns from product_models table
    op.drop_column("product_models", "notes", schema=SCHEMA)
    op.drop_column("product_models", "search_aliases", schema=SCHEMA)
    op.drop_column("product_models", "product_image_url", schema=SCHEMA)
    op.drop_column("product_models", "warranty", schema=SCHEMA)
    op.drop_column("product_models", "color_options", schema=SCHEMA)
    op.drop_column("product_models", "display", schema=SCHEMA)

    # Remove columns from brands table
    op.drop_column("brands", "display_order", schema=SCHEMA)
    op.drop_column("brands", "logo_filename", schema=SCHEMA)
    op.drop_column("brands", "short_name", schema=SCHEMA)
