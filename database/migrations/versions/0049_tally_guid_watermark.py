"""P0 GUID watermark optimization checkpoint fields.

Revision ID: 0049_tally_guid_watermark
Revises: 0048_tally_sync_refinement

Adds diagnostic/optimization checkpoint columns on tally_company_sync.
GUID remains the sole synchronization identity; invoice number and voucher
type are stored for audit and Main Admin diagnostics only.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0049_tally_guid_watermark"
down_revision: str | None = "0048_tally_sync_refinement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "tally_company_sync",
        sa.Column("last_processed_invoice_number", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_processed_voucher_type", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("tally_company_sync", "last_processed_voucher_type", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_processed_invoice_number", schema=SCHEMA)
