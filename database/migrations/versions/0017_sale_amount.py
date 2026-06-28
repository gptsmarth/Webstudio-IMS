"""Add optional sale_amount to sales."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_sale_amount"
down_revision: str | None = "0016_tally_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("sale_amount", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("sales", "sale_amount", schema=SCHEMA)
