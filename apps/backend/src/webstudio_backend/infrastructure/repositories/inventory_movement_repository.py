"""InventoryMovement persistence repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    MovementReason,
    ProductModelStatus,
)
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.inventory_movement import InventoryMovement
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
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemNotFoundError,
    LocationNotFoundError,
    SameLocationMovementError,
    SoldItemCannotMoveError,
    SourceLocationMismatchError,
)


class InventoryMovementRepository(SqlAlchemyRepository[InventoryMovement]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryMovement)

    async def get_by_id(self, entity_id: uuid.UUID) -> InventoryMovement | None:
        return await self._session.get(self._model, entity_id)

    async def create(
        self,
        *,
        inventory_item_id: uuid.UUID,
        from_location_id: int,
        to_location_id: int,
        movement_reason: MovementReason,
        moved_at: datetime,
    ) -> InventoryMovement:
        if from_location_id == to_location_id:
            raise SameLocationMovementError()

        inventory_item = await self._session.get(InventoryItem, inventory_item_id)
        if inventory_item is None:
            raise InventoryItemNotFoundError(str(inventory_item_id))

        if inventory_item.status is InventoryStatus.SOLD:
            raise SoldItemCannotMoveError(str(inventory_item_id))

        if inventory_item.current_location_id != from_location_id:
            raise SourceLocationMismatchError(str(inventory_item_id), from_location_id)

        await self._ensure_active_location(from_location_id)
        await self._ensure_active_location(to_location_id)
        await self._ensure_active_product_model(inventory_item.product_model_id)

        movement = InventoryMovement(
            inventory_item_id=inventory_item_id,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            movement_reason=movement_reason,
            moved_at=moved_at,
        )
        self._session.add(movement)
        inventory_item.current_location_id = to_location_id
        await self._session.flush()
        await self._session.refresh(movement)
        await self._session.refresh(inventory_item)
        return movement

    async def get_latest_by_inventory_item(
        self,
        inventory_item_id: uuid.UUID,
    ) -> InventoryMovement | None:
        statement = (
            select(InventoryMovement)
            .where(InventoryMovement.inventory_item_id == inventory_item_id)
            .order_by(InventoryMovement.moved_at.desc(), InventoryMovement.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def list_by_inventory_item(
        self,
        inventory_item_id: uuid.UUID,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryMovement]:
        statement = select(InventoryMovement).where(
            InventoryMovement.inventory_item_id == inventory_item_id,
        )
        return await self._paginate(statement, page_params, sort_params)

    async def list_history(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryMovement]:
        statement = select(InventoryMovement)
        return await self._paginate(statement, page_params, sort_params)

    async def _paginate(
        self,
        statement: Select[tuple[InventoryMovement]],
        page_params: PageParams,
        sort_params: list[SortParam] | None,
    ) -> PageResult[InventoryMovement]:
        if sort_params:
            column_map = {column.key: column for column in self._model.__table__.columns}
            statement = apply_sorting(statement, sort_params, column_map)
        else:
            statement = statement.order_by(
                InventoryMovement.moved_at.desc(),
                InventoryMovement.created_at.desc(),
            )
        return await paginate(self._session, statement, page_params)

    async def _ensure_active_location(self, location_id: int) -> Location:
        location = await self._session.get(Location, location_id)
        if location is None:
            raise LocationNotFoundError(location_id)
        if not location.is_active:
            raise InactiveLocationError(location_id)
        return location

    async def _ensure_active_product_model(self, product_model_id: uuid.UUID) -> ProductModel:
        product_model = await self._session.get(ProductModel, product_model_id)
        if product_model is None or product_model.status is not ProductModelStatus.ACTIVE:
            raise InactiveProductModelError(str(product_model_id))
        return product_model
