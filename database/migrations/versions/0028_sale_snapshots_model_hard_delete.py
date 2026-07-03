"""Sale product snapshots + permanent product model deletion (replaces archive retention)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_sale_snapshots"
down_revision: str | None = "0027_performance_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.add_column(
        "sales",
        sa.Column("snapshot_serial_number", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_product_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales", sa.Column("snapshot_brand_id", sa.BigInteger(), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_brand_name", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_model_number", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_model_name", sa.String(length=256), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales", sa.Column("snapshot_color", sa.String(length=64), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "sales", sa.Column("snapshot_cpu", sa.String(length=256), nullable=True), schema=SCHEMA
    )
    op.add_column(
        "sales", sa.Column("snapshot_gpu", sa.String(length=256), nullable=True), schema=SCHEMA
    )
    op.add_column("sales", sa.Column("snapshot_ram_gb", sa.Integer(), nullable=True), schema=SCHEMA)
    op.add_column(
        "sales",
        sa.Column("snapshot_storage_value", sa.Numeric(12, 2), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_storage_unit", sa.String(length=16), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_storage_type", sa.String(length=32), nullable=True),
        schema=SCHEMA,
    )
    op.add_column(
        "sales",
        sa.Column("snapshot_location_name", sa.String(length=128), nullable=True),
        schema=SCHEMA,
    )

    op.execute(sa.text(f"""
            UPDATE {SCHEMA}.sales AS sale
            SET
                snapshot_serial_number = item.serial_number,
                snapshot_product_model_id = item.product_model_id,
                snapshot_brand_id = brand.id,
                snapshot_brand_name = brand.name,
                snapshot_model_number = model.model_number,
                snapshot_model_name = model.model_name,
                snapshot_color = item.color,
                snapshot_cpu = model.cpu,
                snapshot_gpu = model.gpu,
                snapshot_ram_gb = model.ram_gb,
                snapshot_storage_value = model.storage_value,
                snapshot_storage_unit = model.storage_unit::text,
                snapshot_storage_type = model.storage_type::text,
                snapshot_location_name = location.name
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            INNER JOIN {SCHEMA}.brands AS brand ON brand.id = model.brand_id
            INNER JOIN {SCHEMA}.locations AS location ON location.id = item.current_location_id
            WHERE sale.inventory_item_id = item.id
              AND sale.snapshot_serial_number IS NULL
            """))

    op.alter_column(
        "sales",
        "inventory_item_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
        schema=SCHEMA,
    )

    op.drop_constraint("fk_sales_inventory_item", "sales", schema=SCHEMA, type_="foreignkey")
    op.create_foreign_key(
        "fk_sales_inventory_item",
        "sales",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )

    # Permanently remove archived models and their inventory units (sales keep snapshot rows).
    op.execute(sa.text(f"""
            UPDATE {SCHEMA}.sales AS sale
            SET inventory_item_id = NULL
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            WHERE sale.inventory_item_id = item.id
              AND model.status = 'archived'
            """))

    op.execute(sa.text(f"""
            UPDATE {SCHEMA}.audit_logs AS log
            SET inventory_item_id = NULL
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            WHERE log.inventory_item_id = item.id
              AND model.status = 'archived'
            """))

    op.execute(sa.text(f"""
            DELETE FROM {SCHEMA}.inventory_items AS item
            USING {SCHEMA}.product_models AS model
            WHERE item.product_model_id = model.id
              AND model.status = 'archived'
            """))

    op.execute(sa.text(f"DELETE FROM {SCHEMA}.product_models WHERE status = 'archived'"))

    op.drop_constraint(
        "fk_audit_logs_inventory_item", "audit_logs", schema=SCHEMA, type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_audit_logs_inventory_item",
        "audit_logs",
        "inventory_items",
        ["inventory_item_id"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema=SCHEMA,
        ondelete="SET NULL",
    )


def downgrade() -> None:
    raise NotImplementedError("0028_sale_snapshots_model_hard_delete is irreversible")
