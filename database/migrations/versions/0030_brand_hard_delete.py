"""Permanently remove archived brands (sales keep snapshot fields)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_brand_hard_delete"
down_revision: str | None = "0029_custom_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "webstudio"


def upgrade() -> None:
    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.sales AS sale
            SET
                snapshot_serial_number = COALESCE(sale.snapshot_serial_number, item.serial_number),
                snapshot_product_model_id = COALESCE(sale.snapshot_product_model_id, item.product_model_id),
                snapshot_brand_id = COALESCE(sale.snapshot_brand_id, brand.id),
                snapshot_brand_name = COALESCE(sale.snapshot_brand_name, brand.name),
                snapshot_model_number = COALESCE(sale.snapshot_model_number, model.model_number),
                snapshot_model_name = COALESCE(sale.snapshot_model_name, model.model_name),
                snapshot_color = COALESCE(sale.snapshot_color, item.color),
                snapshot_cpu = COALESCE(sale.snapshot_cpu, model.cpu),
                snapshot_gpu = COALESCE(sale.snapshot_gpu, model.gpu),
                snapshot_ram_gb = COALESCE(sale.snapshot_ram_gb, model.ram_gb),
                snapshot_storage_value = COALESCE(sale.snapshot_storage_value, model.storage_value),
                snapshot_storage_unit = COALESCE(sale.snapshot_storage_unit, model.storage_unit::text),
                snapshot_storage_type = COALESCE(sale.snapshot_storage_type, model.storage_type::text),
                snapshot_location_name = COALESCE(sale.snapshot_location_name, location.name)
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            INNER JOIN {SCHEMA}.brands AS brand ON brand.id = model.brand_id
            INNER JOIN {SCHEMA}.locations AS location ON location.id = item.current_location_id
            WHERE sale.inventory_item_id = item.id
              AND brand.is_active = false
            """)
    )

    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.sales AS sale
            SET inventory_item_id = NULL
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            INNER JOIN {SCHEMA}.brands AS brand ON brand.id = model.brand_id
            WHERE sale.inventory_item_id = item.id
              AND brand.is_active = false
            """)
    )

    op.execute(
        sa.text(f"""
            UPDATE {SCHEMA}.audit_logs AS log
            SET inventory_item_id = NULL
            FROM {SCHEMA}.inventory_items AS item
            INNER JOIN {SCHEMA}.product_models AS model ON model.id = item.product_model_id
            INNER JOIN {SCHEMA}.brands AS brand ON brand.id = model.brand_id
            WHERE log.inventory_item_id = item.id
              AND brand.is_active = false
            """)
    )

    op.execute(
        sa.text(f"""
            DELETE FROM {SCHEMA}.inventory_items AS item
            USING {SCHEMA}.product_models AS model, {SCHEMA}.brands AS brand
            WHERE item.product_model_id = model.id
              AND model.brand_id = brand.id
              AND brand.is_active = false
            """)
    )

    op.execute(
        sa.text(f"""
            DELETE FROM {SCHEMA}.product_models AS model
            USING {SCHEMA}.brands AS brand
            WHERE model.brand_id = brand.id
              AND brand.is_active = false
            """)
    )

    op.execute(sa.text(f"DELETE FROM {SCHEMA}.brands WHERE is_active = false"))


def downgrade() -> None:
    raise NotImplementedError("0030_brand_hard_delete is irreversible")
