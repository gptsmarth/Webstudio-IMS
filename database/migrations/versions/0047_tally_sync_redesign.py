"""Deterministic Tally sync redesign: serial-only matching, XML archive, decision fields.

Revision ID: 0047_tally_sync_redesign
Revises: 0046_sale_cancellation
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0047_tally_sync_redesign"
down_revision: str | None = "0046_sale_cancellation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        sa.text(
            f"ALTER TYPE {SCHEMA}.{enum_name} ADD VALUE IF NOT EXISTS '{value}'",
        ),
    )


def upgrade() -> None:
    # New line outcomes / voucher statuses (idempotent ADD VALUE).
    _add_enum_value("tally_line_outcome", "additional_product")
    _add_enum_value("tally_line_outcome", "sale_applied_with_review")
    _add_enum_value("tally_line_outcome", "review_required_duplicate_serial")
    _add_enum_value("tally_line_outcome", "review_required_already_sold")
    _add_enum_value("tally_line_outcome", "review_required_not_available")
    _add_enum_value("tally_processing_status", "completed_with_review_required")
    _add_enum_value("tally_processing_status", "skipped")

    # Invoice-level totals + XML archive + review flag.
    op.add_column(
        "tally_processed_invoice",
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("discount_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("round_off", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("cgst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("sgst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("igst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("cess_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("grand_total", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("payment_mode", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("narration", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("review_required", sa.Boolean(), server_default="false", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("raw_xml_gzip", postgresql.BYTEA(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice",
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    # Line-level decision + amount fields.
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("serial_source", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("normalized_serial", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("quantity", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("rate", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("taxable_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("cgst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("sgst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("igst_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("cess_amount", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("line_total", sa.Numeric(18, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("match_result", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("decision", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("decision_reason", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("invoice_model_name", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("ims_model_name", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("sale_id", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("is_additional_product", sa.Boolean(), server_default="false", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "tally_processed_invoice_line",
        sa.Column("review_required", sa.Boolean(), server_default="false", nullable=False),
        schema=SCHEMA,
    )

    # Sale review metadata (Case B / D / E).
    op.add_column(
        "sales",
        sa.Column("review_required", sa.Boolean(), server_default="false", nullable=False),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("review_reason", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("invoice_model_name", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("ims_model_name", sa.String(length=512), nullable=True),
        schema=SCHEMA,
    )

    # Decision log table (immutable per-line decisions).
    op.create_table(
        "tally_line_decision_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tally_processed_invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("tally_processed_invoice_line_id", sa.BigInteger(), nullable=True),
        sa.Column("tally_voucher_guid", sa.String(length=64), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("serial_source", sa.String(length=64), nullable=True),
        sa.Column("extracted_serial", sa.String(length=128), nullable=True),
        sa.Column("normalized_serial", sa.String(length=128), nullable=True),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("match_result", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tally_processed_invoice_id"],
            [f"{SCHEMA}.tally_processed_invoice.id"],
            name="fk_tally_line_decision_log_invoice",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_line_decision_log"),
        schema=SCHEMA,
    )

    # Performance indexes.
    op.create_index(
        "ix_tally_processed_invoice_guid",
        "tally_processed_invoice",
        ["tally_voucher_guid"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_printed_invoice",
        "tally_processed_invoice",
        ["printed_invoice_number"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_imported_at",
        "tally_processed_invoice",
        ["imported_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_line_serial",
        "tally_processed_invoice_line",
        ["serial_number"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_line_normalized_serial",
        "tally_processed_invoice_line",
        ["normalized_serial"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_line_decision_log_guid",
        "tally_line_decision_log",
        ["tally_voucher_guid"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_sales_tally_voucher_guid_review",
        "sales",
        ["tally_voucher_guid", "review_required"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_sales_tally_voucher_guid_review", table_name="sales", schema=SCHEMA)
    op.drop_index(
        "ix_tally_line_decision_log_guid", table_name="tally_line_decision_log", schema=SCHEMA
    )
    op.drop_index(
        "ix_tally_processed_invoice_line_normalized_serial",
        table_name="tally_processed_invoice_line",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_tally_processed_invoice_line_serial",
        table_name="tally_processed_invoice_line",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_tally_processed_invoice_imported_at",
        table_name="tally_processed_invoice",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_tally_processed_invoice_printed_invoice",
        table_name="tally_processed_invoice",
        schema=SCHEMA,
    )
    op.drop_index(
        "ix_tally_processed_invoice_guid", table_name="tally_processed_invoice", schema=SCHEMA
    )
    op.drop_table("tally_line_decision_log", schema=SCHEMA)

    for col in (
        "ims_model_name",
        "invoice_model_name",
        "review_reason",
        "review_required",
    ):
        op.drop_column("sales", col, schema=SCHEMA)

    for col in (
        "review_required",
        "is_additional_product",
        "sale_id",
        "ims_model_name",
        "invoice_model_name",
        "decision_reason",
        "decision",
        "match_result",
        "line_total",
        "cess_amount",
        "igst_amount",
        "sgst_amount",
        "cgst_amount",
        "taxable_amount",
        "rate",
        "quantity",
        "normalized_serial",
        "serial_source",
    ):
        op.drop_column("tally_processed_invoice_line", col, schema=SCHEMA)

    for col in (
        "imported_at",
        "raw_xml_gzip",
        "review_required",
        "narration",
        "payment_mode",
        "grand_total",
        "cess_amount",
        "igst_amount",
        "sgst_amount",
        "cgst_amount",
        "round_off",
        "discount_amount",
        "subtotal",
    ):
        op.drop_column("tally_processed_invoice", col, schema=SCHEMA)
