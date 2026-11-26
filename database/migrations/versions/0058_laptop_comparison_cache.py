"""Add a persistent cache for external laptop comparisons."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0058_laptop_comparison_cache"
down_revision: str | None = "0057_asus_live_price"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "laptop_comparison_cache",
        sa.Column("normalized_brand", sa.String(80), primary_key=True),
        sa.Column("normalized_model", sa.String(160), primary_key=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        schema="webstudio",
    )
    op.create_index(
        "ix_laptop_comparison_cache_expiry",
        "laptop_comparison_cache",
        ["expires_at"],
        schema="webstudio",
    )


def downgrade() -> None:
    op.drop_table("laptop_comparison_cache", schema="webstudio")
