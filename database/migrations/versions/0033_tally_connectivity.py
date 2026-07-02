"""Tally connectivity health columns on tally_company_sync."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_tally_connectivity"
down_revision: str | None = "0032_sales_mapped_loc_null"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "tally_company_sync",
        sa.Column("connectivity_status", sa.String(length=32), nullable=False, server_default="offline"),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_successful_connection_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_failed_connection_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_resolved_ip", sa.String(length=45), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("tally_company_sync", "last_resolved_ip", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_failed_connection_at", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_successful_connection_at", schema=SCHEMA)
    op.drop_column("tally_company_sync", "connectivity_status", schema=SCHEMA)
