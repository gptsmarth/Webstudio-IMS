"""Tally incremental sync engine — history table and fingerprint columns."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_tally_incremental_sync"
down_revision: str | None = "0033_tally_connectivity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "tally_company_sync",
        sa.Column("last_imported_voucher_date", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("consecutive_sync_failures", sa.Integer(), nullable=False, server_default="0"),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("sync_in_progress", sa.Boolean(), nullable=False, server_default="false"),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_sync_duration_ms", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_company_sync",
        sa.Column("last_invoices_imported_count", sa.Integer(), nullable=True),
        schema=SCHEMA,
    )

    op.add_column(
        "tally_processed_invoice",
        sa.Column("voucher_date", sa.Date(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("party_name", sa.String(length=256), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("voucher_amount", sa.Numeric(precision=18, scale=2), nullable=True),
        schema=SCHEMA,
    )

    op.create_index(
        "ix_tally_processed_invoice_fallback_fingerprint",
        "tally_processed_invoice",
        ["tally_company_sync_id", "voucher_date", "tally_voucher_number", "voucher_amount", "party_name"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        "tally_sync_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "tally_company_sync_id",
            sa.BigInteger(),
            sa.ForeignKey(f"{SCHEMA}.tally_company_sync.id", name="fk_tally_sync_history_company_sync"),
            nullable=False,
        ),
        sa.Column("sync_run_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("invoices_checked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoices_imported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoices_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tally_sync_history"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_sync_history_company_started",
        "tally_sync_history",
        ["tally_company_sync_id", "started_at"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_sync_history_sync_run_id",
        "tally_sync_history",
        ["sync_run_id"],
        unique=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_tally_sync_history_sync_run_id", table_name="tally_sync_history", schema=SCHEMA)
    op.drop_index("ix_tally_sync_history_company_started", table_name="tally_sync_history", schema=SCHEMA)
    op.drop_table("tally_sync_history", schema=SCHEMA)
    op.drop_index(
        "ix_tally_processed_invoice_fallback_fingerprint",
        table_name="tally_processed_invoice",
        schema=SCHEMA,
    )
    op.drop_column("tally_processed_invoice", "voucher_amount", schema=SCHEMA)
    op.drop_column("tally_processed_invoice", "party_name", schema=SCHEMA)
    op.drop_column("tally_processed_invoice", "voucher_date", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_invoices_imported_count", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_sync_duration_ms", schema=SCHEMA)
    op.drop_column("tally_company_sync", "sync_in_progress", schema=SCHEMA)
    op.drop_column("tally_company_sync", "consecutive_sync_failures", schema=SCHEMA)
    op.drop_column("tally_company_sync", "last_imported_voucher_date", schema=SCHEMA)
