"""AuditLog persistence repository."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
    paginate,
)
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam, apply_sorting
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.exceptions import InventoryItemNotFoundError


class AuditLogRepository(SqlAlchemyRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)

    async def get_by_id(self, entity_id: uuid.UUID) -> AuditLog | None:
        return await self._session.get(self._model, entity_id)

    async def create(
        self,
        *,
        entity_type: str,
        entity_id: str,
        action: AuditAction,
        actor_user_id: int | None = None,
        actor_display_name: str | None = None,
        actor_role: str | None = None,
        inventory_item_id: uuid.UUID | None = None,
        field_name: str | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        description: str | None = None,
        source: AuditSource = AuditSource.MANUAL,
    ) -> AuditLog:
        return await self.add(
            AuditLog(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
                actor_role=actor_role,
                inventory_item_id=inventory_item_id,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                description=description,
                source=source,
            ),
        )

    async def list(
        self,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[AuditLog]:
        return await self._paginate(select(AuditLog), page_params, sort_params)

    async def search(
        self,
        filters: AuditLogSearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[AuditLog]:
        statement = select(AuditLog)
        statement = await self._apply_filters(statement, filters)
        return await self._paginate(statement, page_params, sort_params)

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: str,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[AuditLog]:
        return await self.search(
            AuditLogSearchFilters(entity_type=entity_type, entity_id=entity_id),
            page_params,
            sort_params,
        )

    async def get_by_inventory_item(
        self,
        inventory_item_id: uuid.UUID,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[AuditLog]:
        return await self.search(
            AuditLogSearchFilters(inventory_item_id=inventory_item_id),
            page_params,
            sort_params,
        )

    async def get_by_serial_number(
        self,
        serial_number: str,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[AuditLog]:
        normalized = serial_number.strip()
        item = await self._session.scalar(
            select(InventoryItem).where(InventoryItem.serial_number == normalized),
        )
        if item is None:
            raise InventoryItemNotFoundError(normalized)
        lifecycle_sort = sort_params or [SortParam(field="created_at", direction="asc")]
        return await self.get_by_inventory_item(item.id, page_params, lifecycle_sort)

    async def _apply_filters(
        self,
        statement: Select[tuple[AuditLog]],
        filters: AuditLogSearchFilters,
    ) -> Select[tuple[AuditLog]]:
        if filters.entity_type is not None:
            statement = statement.where(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id is not None:
            statement = statement.where(AuditLog.entity_id == filters.entity_id)
        if filters.inventory_item_id is not None:
            statement = statement.where(AuditLog.inventory_item_id == filters.inventory_item_id)
        if filters.serial_number is not None:
            normalized = filters.serial_number.strip()
            item = await self._session.scalar(
                select(InventoryItem.id).where(InventoryItem.serial_number == normalized),
            )
            if item is None:
                statement = statement.where(AuditLog.id.is_(None))
            else:
                statement = statement.where(AuditLog.inventory_item_id == item)
        if filters.actor_user_id is not None:
            statement = statement.where(AuditLog.actor_user_id == filters.actor_user_id)
        if filters.action is not None:
            statement = statement.where(AuditLog.action == filters.action)
        if filters.source is not None:
            statement = statement.where(AuditLog.source == filters.source)
        if filters.created_at_from is not None:
            statement = statement.where(AuditLog.created_at >= filters.created_at_from)
        if filters.created_at_to is not None:
            statement = statement.where(AuditLog.created_at <= filters.created_at_to)

        if filters.product_model_id is not None or filters.brand_id is not None:
            inventory_ids = select(InventoryItem.id)
            if filters.product_model_id is not None:
                inventory_ids = inventory_ids.where(
                    InventoryItem.product_model_id == filters.product_model_id,
                )
            if filters.brand_id is not None:
                inventory_ids = inventory_ids.join(ProductModel).where(
                    ProductModel.brand_id == filters.brand_id,
                )
            entity_clauses = [AuditLog.inventory_item_id.in_(inventory_ids)]
            if filters.brand_id is not None:
                entity_clauses.append(
                    (AuditLog.entity_type == "brand") & (AuditLog.entity_id == str(filters.brand_id)),
                )
            if filters.product_model_id is not None:
                entity_clauses.append(
                    (AuditLog.entity_type == "product_model")
                    & (AuditLog.entity_id == str(filters.product_model_id)),
                )
            statement = statement.where(or_(*entity_clauses))

        return statement

    async def _paginate(
        self,
        statement: Select[tuple[AuditLog]],
        page_params: PageParams,
        sort_params: list[SortParam] | None,
    ) -> PageResult[AuditLog]:
        if sort_params:
            column_map = {column.key: column for column in self._model.__table__.columns}
            statement = apply_sorting(statement, sort_params, column_map)
        else:
            statement = statement.order_by(AuditLog.created_at.desc())
        return await paginate(self._session, statement, page_params)
