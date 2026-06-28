"""ProductModel persistence repository."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import Select, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder

from webstudio_backend.infrastructure.database.enums import (
    ProductModelStatus,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateModelNumberError,
    ProductModelHasHistoryError,
)
from webstudio_backend.infrastructure.repositories.product_model_validation import (
    validate_cpu,
    validate_gpu,
    validate_model_name,
    validate_model_number,
    validate_ram_gb,
    validate_status,
    validate_storage_type,
    validate_storage_unit,
    validate_storage_value,
)

SCHEMA = "webstudio"


class ProductModelRepository(SqlAlchemyRepository[ProductModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductModel)

    async def get_by_id(self, entity_id: uuid.UUID) -> ProductModel | None:
        return await self._session.get(self._model, entity_id)

    async def exists(self, brand_id: int, model_number: str) -> bool:
        normalized = validate_model_number(model_number)
        statement = select(ProductModel.id).where(
            ProductModel.brand_id == brand_id,
            ProductModel.model_number == normalized,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None

    async def create(
        self,
        *,
        brand_id: int,
        model_number: str,
        model_name: str,
        cpu: str,
        ram_gb: int,
        storage_value: Decimal,
        storage_unit: StorageUnit,
        storage_type: StorageType,
        gpu: str | None = None,
        status: ProductModelStatus = ProductModelStatus.ACTIVE,
        display: str | None = None,
        color_options: str | None = None,
        product_image_url: str | None = None,
        search_aliases: str | None = None,
        notes: str | None = None,
        actor: AuditActor | None = None,
    ) -> ProductModel:
        payload = self._validated_payload(
            brand_id=brand_id,
            model_number=model_number,
            model_name=model_name,
            cpu=cpu,
            gpu=gpu,
            ram_gb=ram_gb,
            storage_value=storage_value,
            storage_unit=storage_unit,
            storage_type=storage_type,
            status=status,
        )
        payload.update({
            "display": display.strip() if display else None,
            "color_options": color_options.strip() if color_options else None,
            "product_image_url": product_image_url.strip() if product_image_url else None,
            "search_aliases": search_aliases.strip() if search_aliases else None,
            "notes": notes.strip() if notes else None,
        })
        if await self.exists(payload["brand_id"], payload["model_number"]):
            raise DuplicateModelNumberError(payload["brand_id"], payload["model_number"])
        product_model = await self.add(ProductModel(**payload))
        await AuditRecorder(self._session).record_product_model_create(
            product_model,
            actor=actor or AuditActor.system(),
        )
        return product_model

    async def update(
        self,
        product_model: ProductModel,
        *,
        model_number: str | None = None,
        model_name: str | None = None,
        cpu: str | None = None,
        gpu: str | None = None,
        ram_gb: int | None = None,
        storage_value: Decimal | None = None,
        storage_unit: StorageUnit | None = None,
        storage_type: StorageType | None = None,
        display: str | None = None,
        color_options: str | None = None,
        product_image_url: str | None = None,
        search_aliases: str | None = None,
        notes: str | None = None,
        actor: AuditActor | None = None,
    ) -> ProductModel:
        audit_actor = actor or AuditActor.system()
        recorder = AuditRecorder(self._session)
        next_model_number = (
            validate_model_number(model_number)
            if model_number is not None
            else product_model.model_number
        )
        if next_model_number != product_model.model_number:
            if await self.exists(product_model.brand_id, next_model_number):
                raise DuplicateModelNumberError(product_model.brand_id, next_model_number)
            old_value = {"model_number": product_model.model_number}
            product_model.model_number = next_model_number
            await self._session.flush()
            await recorder.record_product_model_field_update(
                product_model,
                field_name="model_number",
                old_value=old_value,
                new_value={"model_number": next_model_number},
                actor=audit_actor,
            )

        if model_name is not None:
            old_value = {"model_name": product_model.model_name}
            product_model.model_name = validate_model_name(model_name)
            if product_model.model_name != old_value["model_name"]:
                await recorder.record_product_model_field_update(
                    product_model,
                    field_name="model_name",
                    old_value=old_value,
                    new_value={"model_name": product_model.model_name},
                    actor=audit_actor,
                )
        if cpu is not None:
            product_model.cpu = validate_cpu(cpu)
        if gpu is not None:
            product_model.gpu = validate_gpu(gpu)
        if ram_gb is not None:
            product_model.ram_gb = validate_ram_gb(ram_gb)
        if storage_value is not None:
            product_model.storage_value = validate_storage_value(storage_value)
        if storage_unit is not None:
            product_model.storage_unit = validate_storage_unit(storage_unit)
        if storage_type is not None:
            product_model.storage_type = validate_storage_type(storage_type)

        # Handle additional fields
        for field, new_val in [
            ("display", display),
            ("color_options", color_options),
            ("product_image_url", product_image_url),
            ("search_aliases", search_aliases),
            ("notes", notes),
        ]:
            if new_val is not None:
                old_val = getattr(product_model, field)
                normalized = new_val.strip() if new_val.strip() else None
                if normalized != old_val:
                    setattr(product_model, field, normalized)
                    await recorder.record_product_model_field_update(
                        product_model,
                        field_name=field,
                        old_value={field: old_val},
                        new_value={field: normalized},
                        actor=audit_actor,
                    )

        await self._session.flush()
        await self._session.refresh(product_model)
        return product_model

    async def archive(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor | None = None,
    ) -> ProductModel:
        product_model.status = ProductModelStatus.ARCHIVED
        await self._session.flush()
        await self._session.refresh(product_model)
        await AuditRecorder(self._session).record_product_model_archive(
            product_model,
            actor=actor or AuditActor.system(),
        )
        return product_model

    async def restore(
        self,
        product_model: ProductModel,
        *,
        actor: AuditActor | None = None,
    ) -> ProductModel:
        product_model.status = ProductModelStatus.ACTIVE
        await self._session.flush()
        await self._session.refresh(product_model)
        await AuditRecorder(self._session).record_product_model_restore(
            product_model,
            actor=actor or AuditActor.system(),
        )
        return product_model

    async def delete(self, product_model: ProductModel) -> None:
        if await self._has_blocking_references(product_model.id):
            raise ProductModelHasHistoryError(str(product_model.id))
        await super().delete(product_model)

    async def find_by_brand(
        self,
        brand_id: int,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ProductModel]:
        statement = select(ProductModel).where(ProductModel.brand_id == brand_id)
        return await self._paginate(statement, page_params, sort_params)

    async def find_active(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ProductModel]:
        statement = select(ProductModel).where(ProductModel.status == ProductModelStatus.ACTIVE)
        return await self._paginate(statement, page_params, sort_params)

    async def find_archived(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ProductModel]:
        statement = select(ProductModel).where(ProductModel.status == ProductModelStatus.ARCHIVED)
        return await self._paginate(statement, page_params, sort_params)

    async def search_by_model_number(
        self,
        query: str,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ProductModel]:
        prefix = query.strip()
        statement = select(ProductModel)
        if prefix:
            statement = statement.where(ProductModel.model_number.ilike(f"{prefix}%"))
        return await self._paginate(statement, page_params, sort_params)

    async def search_by_model_name(
        self,
        query: str,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[ProductModel]:
        prefix = query.strip()
        statement = select(ProductModel)
        if prefix:
            statement = statement.where(ProductModel.model_name.ilike(f"{prefix}%"))
        return await self._paginate(statement, page_params, sort_params)

    async def _paginate(
        self,
        statement: Select[tuple[ProductModel]],
        page_params: PageParams,
        sort_params: list[SortParam] | None,
    ) -> PageResult[ProductModel]:
        if sort_params:
            column_map = {column.key: column for column in self._model.__table__.columns}
            from webstudio_backend.infrastructure.database.repositories.sorting import apply_sorting

            statement = apply_sorting(statement, sort_params, column_map)
        return await paginate(self._session, statement, page_params)

    async def _has_blocking_references(self, product_model_id: uuid.UUID) -> bool:
        if await self._has_inventory_references(product_model_id):
            return True
        if await self._has_sale_references(product_model_id):
            return True
        return await self._has_audit_references(product_model_id)

    async def _has_inventory_references(self, product_model_id: uuid.UUID) -> bool:
        if not await self._table_exists("inventory_items"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.inventory_items
                    WHERE product_model_id = :product_model_id
                )
                """),
            {"product_model_id": product_model_id},
        )
        return bool(result.scalar_one())

    async def _has_sale_references(self, product_model_id: uuid.UUID) -> bool:
        if not await self._table_exists("sales"):
            return False
        if not await self._table_exists("inventory_items"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.sales sale
                    INNER JOIN {SCHEMA}.inventory_items item
                        ON item.id = sale.inventory_item_id
                    WHERE item.product_model_id = :product_model_id
                )
                """),
            {"product_model_id": product_model_id},
        )
        return bool(result.scalar_one())

    async def _has_audit_references(self, product_model_id: uuid.UUID) -> bool:
        if not await self._table_exists("audit_logs"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.audit_logs
                    WHERE entity_type = 'product_model'
                      AND entity_id = :product_model_id
                )
                """),
            {"product_model_id": str(product_model_id)},
        )
        return bool(result.scalar_one())

    async def _table_exists(self, table_name: str) -> bool:
        def check(sync_connection) -> bool:
            inspector = inspect(sync_connection)
            return table_name in inspector.get_table_names(schema=SCHEMA)

        connection = await self._session.connection()
        return await connection.run_sync(check)

    def _validated_payload(
        self,
        *,
        brand_id: int,
        model_number: str,
        model_name: str,
        cpu: str,
        gpu: str | None,
        ram_gb: int,
        storage_value: Decimal,
        storage_unit: StorageUnit,
        storage_type: StorageType,
        status: ProductModelStatus,
    ) -> dict[str, object]:
        return {
            "brand_id": brand_id,
            "model_number": validate_model_number(model_number),
            "model_name": validate_model_name(model_name),
            "cpu": validate_cpu(cpu),
            "gpu": validate_gpu(gpu),
            "ram_gb": validate_ram_gb(ram_gb),
            "storage_value": validate_storage_value(storage_value),
            "storage_unit": validate_storage_unit(storage_unit),
            "storage_type": validate_storage_type(storage_type),
            "status": validate_status(status),
        }
