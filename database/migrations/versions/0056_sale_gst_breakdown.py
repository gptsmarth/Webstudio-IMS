"""Add per-sale CGST/SGST/IGST/cess breakdown columns.

Revision ID: 0056_sale_gst_breakdown
Revises: 0055_cloud_backup_sync

Purely additive: four nullable Numeric(12,2) columns on `sales`. Tally
reports GST as voucher-level ledger entries, not per stock item, so a
sale's tax breakdown is derived by proportionally allocating the
invoice's own CGST/SGST/IGST/cess to each line at sync time (see
webstudio_backend.integrations.tally.gst) rather than re-parsed from
existing rows — historical sales keep these columns NULL until re-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0056_sale_gst_breakdown"
down_revision: str | None = "0055_cloud_backup_sync"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    for column_name in (
        "sale_cgst_amount",
        "sale_sgst_amount",
        "sale_igst_amount",
        "sale_cess_amount",
    ):
        op.add_column(
            "sales",
            sa.Column(column_name, sa.Numeric(12, 2), nullable=True),
            schema=SCHEMA,
        )


def downgrade() -> None:
    for column_name in (
        "sale_cess_amount",
        "sale_igst_amount",
        "sale_sgst_amount",
        "sale_cgst_amount",
    ):
        op.drop_column("sales", column_name, schema=SCHEMA)
