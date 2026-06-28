"""Tally ERP integration tables and sales traceability columns."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_tally_integration"
down_revision: str | None = "0015_remove_warranty_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"

tally_processing_status_enum = postgresql.ENUM(
    "success",
    "partial_success",
    "failed",
    name="tally_processing_status",
    schema=SCHEMA,
    create_type=False,
)

tally_sync_run_status_enum = postgresql.ENUM(
    "success",
    "partial_success",
    "failed",
    "skipped",
    name="tally_sync_run_status",
    schema=SCHEMA,
    create_type=False,
)

tally_line_status_enum = postgresql.ENUM(
    "pending",
    "completed",
    "failed",
    name="tally_line_status",
    schema=SCHEMA,
    create_type=False,
)

tally_line_outcome_enum = postgresql.ENUM(
    "sale_applied",
    "duplicate_sale",
    "serial_number_missing",
    "product_model_missing",
    "product_model_mismatch",
    "ignored",
    "error",
    name="tally_line_outcome",
    schema=SCHEMA,
    create_type=False,
)


def _create_enum(enum_name: str, values: tuple[str, ...]) -> None:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    op.execute(
        sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {SCHEMA}.{enum_name} AS ENUM ({quoted_values});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """),
    )


def _add_enum_value(enum_name: str, value: str) -> None:
    op.execute(
        sa.text(f"""
            DO $$ BEGIN
                ALTER TYPE {SCHEMA}.{enum_name} ADD VALUE IF NOT EXISTS '{value}';
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$;
            """),
    )


def upgrade() -> None:
    _create_enum("tally_processing_status", ("success", "partial_success", "failed"))
    _create_enum("tally_sync_run_status", ("success", "partial_success", "failed", "skipped"))
    _create_enum("tally_line_status", ("pending", "completed", "failed"))
    _create_enum(
        "tally_line_outcome",
        (
            "sale_applied",
            "duplicate_sale",
            "serial_number_missing",
            "product_model_missing",
            "product_model_mismatch",
            "ignored",
            "error",
        ),
    )

    for value in (
        "product_model_mismatch",
        "tally_sync_started",
        "connection_lost",
        "connection_restored",
    ):
        _add_enum_value("notification_type", value)

    op.add_column(
        "sales",
        sa.Column("printed_invoice_number", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("tally_voucher_guid", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("tally_master_id", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("tally_voucher_type", sa.String(length=64), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("mapped_location_id", sa.BigInteger(), nullable=True),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        "fk_sales_mapped_location",
        "sales",
        "locations",
        ["mapped_location_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
    )
    op.create_index("ix_sales_tally_voucher_guid", "sales", ["tally_voucher_guid"], schema=SCHEMA)
    op.create_index("ix_sales_printed_invoice_number", "sales", ["printed_invoice_number"], schema=SCHEMA)

    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.sales
            SET printed_invoice_number = invoice_number
            WHERE printed_invoice_number IS NULL
            """),
    )

    op.create_table(
        "tally_company_sync",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_successful_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_processed_guid", sa.String(length=64), nullable=True),
        sa.Column("last_processed_master_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("connection_status", sa.String(length=32), server_default="disconnected", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_company_sync"),
        sa.UniqueConstraint("company_name", name="uq_tally_company_sync_company_name"),
        schema=SCHEMA,
    )

    op.create_table(
        "tally_processed_invoice",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tally_company_sync_id", sa.BigInteger(), nullable=False),
        sa.Column("tally_voucher_guid", sa.String(length=64), nullable=False),
        sa.Column("tally_master_id", sa.String(length=64), nullable=True),
        sa.Column("tally_voucher_number", sa.String(length=128), nullable=False),
        sa.Column("printed_invoice_number", sa.String(length=128), nullable=True),
        sa.Column("voucher_type", sa.String(length=64), nullable=True),
        sa.Column("processing_status", tally_processing_status_enum, nullable=False),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tally_company_sync_id"],
            [f"{SCHEMA}.tally_company_sync.id"],
            name="fk_tally_processed_invoice_company_sync",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_processed_invoice"),
        sa.UniqueConstraint(
            "tally_company_sync_id",
            "tally_voucher_guid",
            name="uq_tally_processed_invoice_company_guid",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_master_id",
        "tally_processed_invoice",
        ["tally_company_sync_id", "tally_master_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tally_processed_invoice_voucher_number",
        "tally_processed_invoice",
        ["tally_company_sync_id", "tally_voucher_number"],
        schema=SCHEMA,
    )

    op.create_table(
        "tally_processed_invoice_line",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tally_processed_invoice_id", sa.BigInteger(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("serial_number", sa.String(length=128), nullable=True),
        sa.Column("stock_item_name", sa.String(length=512), nullable=True),
        sa.Column("line_status", tally_line_status_enum, nullable=False),
        sa.Column("line_outcome", tally_line_outcome_enum, nullable=True),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tally_processed_invoice_id"],
            [f"{SCHEMA}.tally_processed_invoice.id"],
            name="fk_tally_processed_invoice_line_invoice",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            [f"{SCHEMA}.inventory_items.id"],
            name="fk_tally_processed_invoice_line_inventory",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_processed_invoice_line"),
        sa.UniqueConstraint(
            "tally_processed_invoice_id",
            "line_index",
            name="uq_tally_processed_invoice_line_index",
        ),
        schema=SCHEMA,
    )

    op.create_table(
        "tally_sync_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sync_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tally_company_sync_id", sa.BigInteger(), nullable=False),
        sa.Column("tally_processed_invoice_id", sa.BigInteger(), nullable=True),
        sa.Column("tally_voucher_guid", sa.String(length=64), nullable=True),
        sa.Column("tally_voucher_number", sa.String(length=128), nullable=True),
        sa.Column("printed_invoice_number", sa.String(length=128), nullable=True),
        sa.Column("voucher_type", sa.String(length=64), nullable=True),
        sa.Column("sync_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_duration_ms", sa.Integer(), nullable=True),
        sa.Column("processing_status", tally_sync_run_status_enum, nullable=False),
        sa.Column("inventory_item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("successfully_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("already_sold", sa.Integer(), server_default="0", nullable=False),
        sa.Column("missing_serial", sa.Integer(), server_default="0", nullable=False),
        sa.Column("missing_model", sa.Integer(), server_default="0", nullable=False),
        sa.Column("model_mismatches", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ignored_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_details", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.String(length=256), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tally_company_sync_id"],
            [f"{SCHEMA}.tally_company_sync.id"],
            name="fk_tally_sync_log_company_sync",
        ),
        sa.ForeignKeyConstraint(
            ["tally_processed_invoice_id"],
            [f"{SCHEMA}.tally_processed_invoice.id"],
            name="fk_tally_sync_log_processed_invoice",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tally_sync_log"),
        schema=SCHEMA,
    )
    op.create_index("ix_tally_sync_log_run_id", "tally_sync_log", ["sync_run_id"], schema=SCHEMA)
    op.create_index(
        "ix_tally_sync_log_started_at",
        "tally_sync_log",
        ["sync_started_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_tally_sync_log_started_at", table_name="tally_sync_log", schema=SCHEMA)
    op.drop_index("ix_tally_sync_log_run_id", table_name="tally_sync_log", schema=SCHEMA)
    op.drop_table("tally_sync_log", schema=SCHEMA)
    op.drop_table("tally_processed_invoice_line", schema=SCHEMA)
    op.drop_index("ix_tally_processed_invoice_voucher_number", table_name="tally_processed_invoice", schema=SCHEMA)
    op.drop_index("ix_tally_processed_invoice_master_id", table_name="tally_processed_invoice", schema=SCHEMA)
    op.drop_table("tally_processed_invoice", schema=SCHEMA)
    op.drop_table("tally_company_sync", schema=SCHEMA)
    op.drop_index("ix_sales_printed_invoice_number", table_name="sales", schema=SCHEMA)
    op.drop_index("ix_sales_tally_voucher_guid", table_name="sales", schema=SCHEMA)
    op.drop_constraint("fk_sales_mapped_location", "sales", schema=SCHEMA, type_="foreignkey")
    op.drop_column("sales", "mapped_location_id", schema=SCHEMA)
    op.drop_column("sales", "tally_voucher_type", schema=SCHEMA)
    op.drop_column("sales", "tally_master_id", schema=SCHEMA)
    op.drop_column("sales", "tally_voucher_guid", schema=SCHEMA)
    op.drop_column("sales", "printed_invoice_number", schema=SCHEMA)
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.tally_line_outcome"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.tally_line_status"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.tally_sync_run_status"))
    op.execute(sa.text(f"DROP TYPE IF EXISTS {SCHEMA}.tally_processing_status"))
