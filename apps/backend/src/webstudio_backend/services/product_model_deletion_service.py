"""Permanent product model deletion with inventory cascade and sales preservation."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.catalogue_deletion import ProductModelDeletePreviewResponse
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)

_SCHEMA = DATABASE_SCHEMA


class ProductModelDeletionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._product_models = ProductModelRepository(session)
        self._recorder = AuditRecorder(session)

    async def preview(self, product_model: ProductModel) -> ProductModelDeletePreviewResponse:
        inventory_count = await self._product_models.count_inventory_items(product_model.id)
        return ProductModelDeletePreviewResponse(
            inventory_count=inventory_count,
            # Cascade deletes inventory units; sales/audit history stay via snapshots.
            can_delete=True,
        )

    async def delete_product_model(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor,
    ) -> None:
        await self._cascade_clear_inventory(product_model.id)
        await self._product_models.force_delete(product_model)
        await self._recorder.record_product_model_delete(product_model, actor=actor)

    async def _cascade_clear_inventory(self, product_model_id: uuid.UUID) -> None:
        """Remove inventory for this model while preserving sales history snapshots.

        Order matches migration 0028/0030 purge: backfill snapshots → null FKs →
        delete inventory rows. Sales rows themselves are never deleted.
        """
        params = {"product_model_id": product_model_id}

        await self._session.execute(
            text(f"""
                UPDATE {_SCHEMA}.sales AS sale
                SET
                    snapshot_serial_number = COALESCE(
                        sale.snapshot_serial_number, item.serial_number
                    ),
                    snapshot_product_model_id = COALESCE(
                        sale.snapshot_product_model_id, item.product_model_id
                    ),
                    snapshot_brand_id = COALESCE(sale.snapshot_brand_id, brand.id),
                    snapshot_brand_name = COALESCE(sale.snapshot_brand_name, brand.name),
                    snapshot_model_number = COALESCE(
                        sale.snapshot_model_number, model.model_number
                    ),
                    snapshot_model_name = COALESCE(sale.snapshot_model_name, model.model_name),
                    snapshot_color = COALESCE(sale.snapshot_color, item.color),
                    snapshot_cpu = COALESCE(sale.snapshot_cpu, model.cpu),
                    snapshot_gpu = COALESCE(sale.snapshot_gpu, model.gpu),
                    snapshot_ram_gb = COALESCE(sale.snapshot_ram_gb, model.ram_gb),
                    snapshot_storage_value = COALESCE(
                        sale.snapshot_storage_value, model.storage_value
                    ),
                    snapshot_storage_unit = COALESCE(
                        sale.snapshot_storage_unit, model.storage_unit::text
                    ),
                    snapshot_storage_type = COALESCE(
                        sale.snapshot_storage_type, model.storage_type::text
                    ),
                    snapshot_location_name = COALESCE(
                        sale.snapshot_location_name, location.name
                    ),
                    snapshot_purchase_price = COALESCE(
                        sale.snapshot_purchase_price, item.purchase_price
                    )
                FROM {_SCHEMA}.inventory_items AS item
                INNER JOIN {_SCHEMA}.product_models AS model
                    ON model.id = item.product_model_id
                INNER JOIN {_SCHEMA}.brands AS brand ON brand.id = model.brand_id
                INNER JOIN {_SCHEMA}.locations AS location
                    ON location.id = item.current_location_id
                WHERE sale.inventory_item_id = item.id
                  AND item.product_model_id = :product_model_id
                """),
            params,
        )

        for table in (
            "sales",
            "audit_logs",
            "notifications",
            "tally_processed_invoice_line",
            "tally_line_decision_log",
        ):
            await self._session.execute(
                text(f"""
                    UPDATE {_SCHEMA}.{table} AS target
                    SET inventory_item_id = NULL
                    FROM {_SCHEMA}.inventory_items AS item
                    WHERE target.inventory_item_id = item.id
                      AND item.product_model_id = :product_model_id
                    """),
                params,
            )

        await self._session.execute(
            text(f"""
                DELETE FROM {_SCHEMA}.inventory_items
                WHERE product_model_id = :product_model_id
                """),
            params,
        )
