"""InventoryItem persistence repository."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import InventoryStatus, ProductModelStatus
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.database.repositories.sorting import (
    SortParam,
    apply_sorting,
)
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemDeleteNotAllowedError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_filters import (
    InventorySearchFilters,
)
from webstudio_backend.infrastructure.repositories.inventory_item_validation import (
    validate_color,
    validate_serial_number,
    validate_status,
)

SCHEMA = "webstudio"


class InventoryItemRepository(SqlAlchemyRepository[InventoryItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryItem)

    async def get_by_id(self, entity_id: uuid.UUID) -> InventoryItem | None:
        return await self._session.get(self._model, entity_id)

    async def find_by_serial_number(self, serial_number: str) -> InventoryItem | None:
        normalized = validate_serial_number(serial_number)
        statement = select(InventoryItem).where(InventoryItem.serial_number == normalized)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        serial_number: str,
        product_model_id: uuid.UUID,
        color: str,
        current_location_id: int,
        status: InventoryStatus,
    ) -> InventoryItem:
        normalized_serial = validate_serial_number(serial_number)
        normalized_color = validate_color(color)
        validated_status = validate_status(status)

        if await self.find_by_serial_number(normalized_serial) is not None:
            raise DuplicateSerialNumberError(normalized_serial)

        await self._ensure_active_product_model(product_model_id)
        await self._ensure_active_location(current_location_id)

        return await self.add(
            InventoryItem(
                serial_number=normalized_serial,
                product_model_id=product_model_id,
                color=normalized_color,
                current_location_id=current_location_id,
                status=validated_status,
            ),
        )

    async def update(
        self,
        inventory_item: InventoryItem,
        *,
        product_model_id: uuid.UUID | None = None,
        color: str | None = None,
        current_location_id: int | None = None,
        status: InventoryStatus | None = None,
    ) -> InventoryItem:
        if product_model_id is not None:
            await self._ensure_active_product_model(product_model_id)
            inventory_item.product_model_id = product_model_id
        if color is not None:
            inventory_item.color = validate_color(color)
        if current_location_id is not None:
            await self._ensure_active_location(current_location_id)
            inventory_item.current_location_id = current_location_id
        if status is not None:
            inventory_item.status = validate_status(status)

        await self._session.flush()
        await self._session.refresh(inventory_item)
        return inventory_item

    async def delete(self, inventory_item: InventoryItem) -> None:
        reason = await self._delete_block_reason(inventory_item)
        if reason is not None:
            raise InventoryItemDeleteNotAllowedError(str(inventory_item.id), reason)
        await super().delete(inventory_item)

    async def search(
        self,
        filters: InventorySearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        statement = select(InventoryItem)
        statement = self._apply_filters(statement, filters)
        return await self._paginate(statement, page_params, sort_params)

    async def filter_by_brand(
        self,
        brand_id: int,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        return await self.search(
            InventorySearchFilters(brand_id=brand_id),
            page_params,
            sort_params,
        )

    async def filter_by_product_model(
        self,
        product_model_id: uuid.UUID,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        return await self.search(
            InventorySearchFilters(product_model_id=product_model_id),
            page_params,
            sort_params,
        )

    async def filter_by_color(
        self,
        color: str,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        return await self.search(
            InventorySearchFilters(color=color),
            page_params,
            sort_params,
        )

    async def filter_by_location(
        self,
        current_location_id: int,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        return await self.search(
            InventorySearchFilters(current_location_id=current_location_id),
            page_params,
            sort_params,
        )

    async def filter_by_status(
        self,
        status: InventoryStatus,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItem]:
        return await self.search(
            InventorySearchFilters(status=status),
            page_params,
            sort_params,
        )

    def _apply_filters(
        self,
        statement: Select[tuple[InventoryItem]],
        filters: InventorySearchFilters,
    ) -> Select[tuple[InventoryItem]]:
        if filters.brand_id is not None:
            statement = statement.join(ProductModel).where(
                ProductModel.brand_id == filters.brand_id,
            )

        if filters.product_model_id is not None:
            statement = statement.where(
                InventoryItem.product_model_id == filters.product_model_id,
            )
        if filters.color is not None:
            statement = statement.where(InventoryItem.color.ilike(filters.color.strip()))
        if filters.current_location_id is not None:
            statement = statement.where(
                InventoryItem.current_location_id == filters.current_location_id,
            )
        if filters.status is not None:
            statement = statement.where(InventoryItem.status == filters.status)
        if filters.search:
            prefix = filters.search.strip()
            if prefix:
                statement = statement.where(InventoryItem.serial_number.ilike(f"{prefix}%"))
        return statement

    async def _paginate(
        self,
        statement: Select[tuple[InventoryItem]],
        page_params: PageParams,
        sort_params: list[SortParam] | None,
    ) -> PageResult[InventoryItem]:
        if sort_params:
            column_map = {column.key: column for column in self._model.__table__.columns}
            statement = apply_sorting(statement, sort_params, column_map)
        return await paginate(self._session, statement, page_params)

    async def _ensure_active_product_model(self, product_model_id: uuid.UUID) -> ProductModel:
        product_model = await self._session.get(ProductModel, product_model_id)
        if product_model is None or product_model.status is not ProductModelStatus.ACTIVE:
            raise InactiveProductModelError(str(product_model_id))
        return product_model

    async def _ensure_active_location(self, location_id: int) -> Location:
        location = await self._session.get(Location, location_id)
        if location is None or not location.is_active:
            raise InactiveLocationError(location_id)
        return location

    async def _delete_block_reason(self, inventory_item: InventoryItem) -> str | None:
        if inventory_item.status is InventoryStatus.SOLD:
            return "item is sold"
        if await self._has_movement_references(inventory_item.id):
            return "movement references exist"
        if await self._has_sale_references(inventory_item.id):
            return "sale references exist"
        if await self._has_audit_references(inventory_item.id):
            return "audit references exist"
        return None

    async def _has_movement_references(self, inventory_item_id: uuid.UUID) -> bool:
        if not await self._table_exists("inventory_movements"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.inventory_movements
                    WHERE inventory_item_id = :inventory_item_id
                )
                """),
            {"inventory_item_id": inventory_item_id},
        )
        return bool(result.scalar_one())

    async def _has_sale_references(self, inventory_item_id: uuid.UUID) -> bool:
        if not await self._table_exists("sales"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.sales
                    WHERE inventory_item_id = :inventory_item_id
                )
                """),
            {"inventory_item_id": inventory_item_id},
        )
        return bool(result.scalar_one())

    async def _has_audit_references(self, inventory_item_id: uuid.UUID) -> bool:
        if not await self._table_exists("audit_logs"):
            return False
        result = await self._session.execute(
            text(f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {SCHEMA}.audit_logs
                    WHERE entity_type = 'inventory_item'
                      AND entity_id = :inventory_item_id
                )
                """),
            {"inventory_item_id": str(inventory_item_id)},
        )
        return bool(result.scalar_one())

    async def _table_exists(self, table_name: str) -> bool:
        def check(sync_connection) -> bool:
            inspector = inspect(sync_connection)
            return table_name in inspector.get_table_names(schema=SCHEMA)

        connection = await self._session.connection()
        return await connection.run_sync(check)
