"""InventoryItem persistence repository."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Select, func, inspect, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import (
    InventorySource,
    InventoryStatus,
    ProductModelStatus,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
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
    ArchivedInventoryOperationError,
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemArchiveNotAllowedError,
    InventoryItemDeleteNotAllowedError,
    InventoryItemNotFoundError,
    LocationNotFoundError,
    SameLocationMovementError,
    SoldItemCannotMoveError,
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


@dataclass(frozen=True, slots=True)
class InventoryItemDetailRow:
    item: InventoryItem
    product_model: ProductModel
    brand: Brand
    location: Location


class InventoryItemRepository(SqlAlchemyRepository[InventoryItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryItem)

    async def get_by_id(self, entity_id: uuid.UUID) -> InventoryItem | None:
        return await self._session.get(self._model, entity_id)

    async def find_by_serial_number(self, serial_number: str) -> InventoryItem | None:
        matches = await self.find_all_by_serial_number(serial_number)
        if not matches:
            return None
        if len(matches) > 1:
            # Ambiguous — callers must use find_all_by_serial_number for Case D.
            return matches[0]
        return matches[0]

    async def find_all_by_serial_number(self, serial_number: str) -> list[InventoryItem]:
        normalized = validate_serial_number(serial_number)
        statement = select(InventoryItem).where(
            func.lower(InventoryItem.serial_number) == normalized.lower(),
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_detail_by_serial(self, serial_number: str) -> InventoryItemDetailRow | None:
        normalized = validate_serial_number(serial_number)
        statement = (
            self._detail_select()
            .where(func.lower(InventoryItem.serial_number) == normalized.lower())
            .limit(1)
        )
        result = await self._session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return None
        item, product_model, brand, location = row
        return InventoryItemDetailRow(
            item=item,
            product_model=product_model,
            brand=brand,
            location=location,
        )

    def _detail_select(self) -> Select[tuple[InventoryItem, ProductModel, Brand, Location]]:
        return (
            select(InventoryItem, ProductModel, Brand, Location)
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .join(Brand, ProductModel.brand_id == Brand.id)
            .join(Location, InventoryItem.current_location_id == Location.id)
        )

    async def get_detail(self, entity_id: uuid.UUID) -> InventoryItemDetailRow | None:
        statement = self._detail_select().where(InventoryItem.id == entity_id)
        result = await self._session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return None
        item, product_model, brand, location = row
        return InventoryItemDetailRow(
            item=item,
            product_model=product_model,
            brand=brand,
            location=location,
        )

    async def require_by_id(self, entity_id: uuid.UUID) -> InventoryItem:
        item = await self.get_by_id(entity_id)
        if item is None:
            raise InventoryItemNotFoundError(str(entity_id))
        return item

    async def create(
        self,
        *,
        serial_number: str,
        product_model_id: uuid.UUID,
        color: str,
        current_location_id: int,
        status: InventoryStatus,
        purchase_date: date | None = None,
        purchase_price: Decimal | None = None,
        inventory_source: InventorySource = InventorySource.MANUAL,
        actor: AuditActor | None = None,
    ) -> InventoryItem:
        normalized_serial = validate_serial_number(serial_number)
        normalized_color = validate_color(color)
        validated_status = validate_status(status)

        product_model = await self._ensure_active_product_model(product_model_id)
        await self._ensure_active_location(current_location_id)

        # EAN-as-serial brands may share a serial across units; all other brands
        # keep the globally-unique-serial guard exactly as before.
        serial_is_shared = await self._brand_allows_shared_serials(product_model.brand_id)
        if not serial_is_shared and await self.find_by_serial_number(normalized_serial) is not None:
            raise DuplicateSerialNumberError(normalized_serial)

        item = await self.add(
            InventoryItem(
                serial_number=normalized_serial,
                serial_is_shared=serial_is_shared,
                product_model_id=product_model_id,
                color=normalized_color,
                current_location_id=current_location_id,
                status=validated_status,
                purchase_date=purchase_date,
                purchase_price=purchase_price,
                inventory_source=inventory_source,
            ),
        )
        await AuditRecorder(self._session).record_inventory_create(
            item,
            actor=actor or AuditActor.system(),
        )
        return item

    async def update(
        self,
        inventory_item: InventoryItem,
        *,
        serial_number: str | None = None,
        product_model_id: uuid.UUID | None = None,
        color: str | None = None,
        status: InventoryStatus | None = None,
        purchase_date: date | None = None,
        set_purchase_date: bool = False,
        purchase_price: Decimal | None = None,
        set_purchase_price: bool = False,
        actor: AuditActor | None = None,
    ) -> InventoryItem:
        audit_actor = actor or AuditActor.system()
        recorder = AuditRecorder(self._session)
        old_status = inventory_item.status
        old_serial = inventory_item.serial_number
        old_color = inventory_item.color
        old_product_model_id = inventory_item.product_model_id
        old_purchase_date = inventory_item.purchase_date
        old_purchase_price = inventory_item.purchase_price

        if serial_number is not None:
            normalized_serial = validate_serial_number(serial_number)
            if normalized_serial.lower() != inventory_item.serial_number.lower():
                existing = await self.find_by_serial_number(normalized_serial)
                if existing is not None and existing.id != inventory_item.id:
                    raise DuplicateSerialNumberError(normalized_serial)
                inventory_item.serial_number = normalized_serial
        if product_model_id is not None:
            await self._ensure_active_product_model(product_model_id)
            inventory_item.product_model_id = product_model_id
        if color is not None:
            inventory_item.color = validate_color(color)
        if status is not None:
            inventory_item.status = validate_status(status)
        if set_purchase_date:
            inventory_item.purchase_date = purchase_date
        if set_purchase_price:
            inventory_item.purchase_price = purchase_price

        await self._session.flush()
        await self._session.refresh(inventory_item)

        if serial_number is not None and inventory_item.serial_number != old_serial:
            await recorder.record_inventory_field_update(
                inventory_item,
                field_name="serial_number",
                old_value={"serial_number": old_serial},
                new_value={"serial_number": inventory_item.serial_number},
                actor=audit_actor,
            )
        if status is not None and status != old_status:
            await recorder.record_inventory_status_change(
                inventory_item,
                old_status=old_status,
                new_status=status,
                actor=audit_actor,
            )
        if product_model_id is not None and product_model_id != old_product_model_id:
            await recorder.record_inventory_product_model_change(
                inventory_item,
                old_product_model_id=old_product_model_id,
                new_product_model_id=product_model_id,
                actor=audit_actor,
            )
        if color is not None and inventory_item.color != old_color:
            await recorder.record_inventory_field_update(
                inventory_item,
                field_name="color",
                old_value={"color": old_color},
                new_value={"color": inventory_item.color},
                actor=audit_actor,
            )
        if set_purchase_date and inventory_item.purchase_date != old_purchase_date:
            await recorder.record_inventory_field_update(
                inventory_item,
                field_name="purchase_date",
                old_value={
                    "purchase_date": old_purchase_date.isoformat() if old_purchase_date else None
                },
                new_value={
                    "purchase_date": (
                        inventory_item.purchase_date.isoformat()
                        if inventory_item.purchase_date
                        else None
                    )
                },
                actor=audit_actor,
            )
        if set_purchase_price and inventory_item.purchase_price != old_purchase_price:
            await recorder.record_inventory_field_update(
                inventory_item,
                field_name="purchase_price",
                old_value={
                    "purchase_price": (
                        float(old_purchase_price) if old_purchase_price is not None else None
                    )
                },
                new_value={
                    "purchase_price": (
                        float(inventory_item.purchase_price)
                        if inventory_item.purchase_price is not None
                        else None
                    )
                },
                actor=audit_actor,
            )

        return inventory_item

    async def transfer_location(
        self,
        inventory_item: InventoryItem,
        *,
        to_location_id: int,
        actor: AuditActor,
    ) -> InventoryItem:
        if inventory_item.is_archived:
            raise ArchivedInventoryOperationError(str(inventory_item.id), "moved")
        if inventory_item.status is InventoryStatus.SOLD:
            raise SoldItemCannotMoveError(str(inventory_item.id))
        if to_location_id == inventory_item.current_location_id:
            raise SameLocationMovementError()

        location = await self._session.get(Location, to_location_id)
        if location is None:
            raise LocationNotFoundError(to_location_id)
        if not location.is_active:
            raise InactiveLocationError(to_location_id)

        old_location_id = inventory_item.current_location_id
        inventory_item.current_location_id = to_location_id
        await self._session.flush()
        await self._session.refresh(inventory_item)
        await AuditRecorder(self._session).record_inventory_location_change(
            inventory_item,
            old_location_id=old_location_id,
            new_location_id=to_location_id,
            actor=actor,
        )
        return inventory_item

    async def count_at_location(self, location_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(InventoryItem)
            .where(InventoryItem.current_location_id == location_id)
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def reassign_location_for_deletion(
        self,
        inventory_item: InventoryItem,
        *,
        to_location_id: int,
        actor: AuditActor,
    ) -> InventoryItem:
        if to_location_id == inventory_item.current_location_id:
            return inventory_item

        location = await self._session.get(Location, to_location_id)
        if location is None:
            raise LocationNotFoundError(to_location_id)

        old_location_id = inventory_item.current_location_id
        inventory_item.current_location_id = to_location_id
        await self._session.flush()
        await self._session.refresh(inventory_item)
        await AuditRecorder(self._session).record_inventory_location_change(
            inventory_item,
            old_location_id=old_location_id,
            new_location_id=to_location_id,
            actor=actor,
        )
        return inventory_item

    async def transfer_all_for_location_deletion(
        self,
        from_location_id: int,
        to_location_id: int,
        *,
        actor: AuditActor,
    ) -> int:
        if from_location_id == to_location_id:
            raise SameLocationMovementError()

        statement = select(InventoryItem).where(
            InventoryItem.current_location_id == from_location_id,
        )
        result = await self._session.execute(statement)
        items = list(result.scalars().all())
        for item in items:
            await self.reassign_location_for_deletion(
                item,
                to_location_id=to_location_id,
                actor=actor,
            )
        return len(items)

    async def count_movable_at_location(self, location_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(InventoryItem)
            .where(
                InventoryItem.current_location_id == location_id,
                InventoryItem.is_archived.is_(False),
                InventoryItem.status != InventoryStatus.SOLD,
            )
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one() or 0)

    async def transfer_all_movable_from_location(
        self,
        from_location_id: int,
        to_location_id: int,
        *,
        actor: AuditActor,
    ) -> int:
        statement = select(InventoryItem).where(
            InventoryItem.current_location_id == from_location_id,
            InventoryItem.is_archived.is_(False),
            InventoryItem.status != InventoryStatus.SOLD,
        )
        result = await self._session.execute(statement)
        items = list(result.scalars().all())
        for item in items:
            await self.transfer_location(item, to_location_id=to_location_id, actor=actor)
        return len(items)

    async def archive(
        self,
        inventory_item: InventoryItem,
        *,
        actor: AuditActor | None = None,
    ) -> InventoryItem:
        if inventory_item.is_archived:
            return inventory_item
        if inventory_item.status is InventoryStatus.SOLD:
            raise InventoryItemArchiveNotAllowedError(str(inventory_item.id), "item is sold")
        inventory_item.is_archived = True
        await self._session.flush()
        await AuditRecorder(self._session).record_inventory_archive(
            inventory_item,
            actor=actor or AuditActor.system(),
        )
        return inventory_item

    async def restore(
        self,
        inventory_item: InventoryItem,
        *,
        actor: AuditActor | None = None,
    ) -> InventoryItem:
        if not inventory_item.is_archived:
            return inventory_item
        inventory_item.is_archived = False
        await self._session.flush()
        await AuditRecorder(self._session).record_inventory_restore(
            inventory_item,
            actor=actor or AuditActor.system(),
        )
        return inventory_item

    async def delete(self, inventory_item: InventoryItem) -> None:
        reason = await self._delete_block_reason(inventory_item)
        if reason is not None:
            raise InventoryItemDeleteNotAllowedError(str(inventory_item.id), reason)
        await super().delete(inventory_item)

    async def list_for_product_model(self, product_model_id: uuid.UUID) -> list[InventoryItem]:
        statement = select(InventoryItem).where(InventoryItem.product_model_id == product_model_id)
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def delete_unsold_item(
        self,
        inventory_item: InventoryItem,
        *,
        actor: AuditActor | None = None,
    ) -> None:
        """Permanently remove an unsold inventory unit from live stock.

        Sales history is never deleted — items with sale rows are blocked.
        Audit/notification FKs are cleared so create/update audit does not block.
        """
        if inventory_item.status is InventoryStatus.SOLD:
            raise InventoryItemDeleteNotAllowedError(str(inventory_item.id), "item is sold")
        if await self._has_sale_references(inventory_item.id):
            raise InventoryItemDeleteNotAllowedError(
                str(inventory_item.id), "sale references exist"
            )

        item_id = inventory_item.id
        await AuditRecorder(self._session).record_inventory_delete(
            inventory_item,
            actor=actor or AuditActor.system(),
        )

        params = {"inventory_item_id": item_id}
        for table in (
            "sales",
            "audit_logs",
            "notifications",
            "tally_processed_invoice_line",
            "tally_line_decision_log",
        ):
            await self._session.execute(
                text(f"""
                    UPDATE {SCHEMA}.{table}
                    SET inventory_item_id = NULL
                    WHERE inventory_item_id = :inventory_item_id
                    """),
                params,
            )

        await self.force_delete(inventory_item)

    async def search(
        self,
        filters: InventorySearchFilters,
        page_params: PageParams,
        sort_params: list[SortParam] | None = None,
    ) -> PageResult[InventoryItemDetailRow]:
        if filters.serial_number and filters.serial_number.strip():
            detail = await self.get_detail_by_serial(filters.serial_number)
            items = [detail] if detail is not None else []
            total = len(items)
            return PageResult(
                items=items,
                page=1,
                page_size=page_params.page_size,
                total_items=total,
            )

        base = self._detail_select()
        filtered = self._apply_filters(base, filters)

        count_statement = select(func.count()).select_from(
            filtered.with_only_columns(InventoryItem.id).order_by(None).subquery(),
        )
        total = int((await self._session.scalar(count_statement)) or 0)

        if sort_params:
            column_map = {column.key: column for column in InventoryItem.__table__.columns}
            filtered = apply_sorting(filtered, sort_params, column_map)
        else:
            filtered = filtered.order_by(InventoryItem.updated_at.desc())

        offset = (page_params.page - 1) * page_params.page_size
        paged = filtered.offset(offset).limit(page_params.page_size)
        result = await self._session.execute(paged)
        items = [
            InventoryItemDetailRow(item=item, product_model=pm, brand=brand, location=location)
            for item, pm, brand, location in result.all()
        ]
        return PageResult(
            items=items,
            page=page_params.page,
            page_size=page_params.page_size,
            total_items=total,
        )

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
        statement: Select[tuple[InventoryItem, ProductModel, Brand, Location]],
        filters: InventorySearchFilters,
    ) -> Select[tuple[InventoryItem, ProductModel, Brand, Location]]:
        if filters.is_archived is not None:
            statement = statement.where(InventoryItem.is_archived.is_(filters.is_archived))
        elif not filters.include_archived:
            statement = statement.where(InventoryItem.is_archived.is_(False))

        if filters.brand_id is not None:
            statement = statement.where(Brand.id == filters.brand_id)
        if filters.product_model_id is not None:
            statement = statement.where(InventoryItem.product_model_id == filters.product_model_id)
        if filters.color is not None:
            statement = statement.where(InventoryItem.color.ilike(f"%{filters.color.strip()}%"))
        if filters.current_location_id is not None:
            statement = statement.where(
                InventoryItem.current_location_id == filters.current_location_id
            )
        if filters.status is not None:
            statement = statement.where(InventoryItem.status == filters.status)
        if filters.serial_number is not None:
            normalized = filters.serial_number.strip()
            if normalized:
                statement = statement.where(
                    func.lower(InventoryItem.serial_number) == normalized.lower(),
                )
        if filters.brand_name is not None:
            term = filters.brand_name.strip()
            if term:
                statement = statement.where(Brand.name.ilike(f"%{term}%"))
        if filters.product_model is not None:
            term = filters.product_model.strip()
            if term:
                statement = statement.where(
                    or_(
                        ProductModel.model_number.ilike(f"%{term}%"),
                        ProductModel.model_name.ilike(f"%{term}%"),
                    ),
                )
        if filters.location_name is not None:
            term = filters.location_name.strip()
            if term:
                statement = statement.where(Location.name.ilike(f"%{term}%"))
        if filters.search:
            prefix = filters.search.strip()
            if prefix:
                like_term = f"%{prefix}%"
                sale_match = (
                    select(Sale.id)
                    .where(Sale.inventory_item_id == InventoryItem.id)
                    .where(
                        or_(
                            Sale.invoice_number.ilike(like_term),
                            Sale.customer_name.ilike(like_term),
                        ),
                    )
                    .correlate(InventoryItem)
                    .exists()
                )
                statement = statement.where(
                    or_(
                        InventoryItem.serial_number.ilike(f"{prefix}%"),
                        ProductModel.model_number.ilike(like_term),
                        ProductModel.model_name.ilike(like_term),
                        Brand.name.ilike(like_term),
                        Location.name.ilike(like_term),
                        sale_match,
                    ),
                )
        if filters.purchase_date_from is not None:
            statement = statement.where(InventoryItem.purchase_date >= filters.purchase_date_from)
        if filters.purchase_date_to is not None:
            statement = statement.where(InventoryItem.purchase_date <= filters.purchase_date_to)
        if filters.created_at_from is not None:
            statement = statement.where(
                InventoryItem.created_at >= datetime.combine(filters.created_at_from, time.min),
            )
        if filters.created_at_to is not None:
            statement = statement.where(
                InventoryItem.created_at <= datetime.combine(filters.created_at_to, time.max),
            )
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

    async def _brand_allows_shared_serials(self, brand_id: int) -> bool:
        statement = select(Brand.allow_duplicate_serials).where(Brand.id == brand_id)
        result = await self._session.execute(statement)
        return bool(result.scalar_one_or_none())

    async def find_available_shared_units_fifo(
        self,
        *,
        serial_number: str,
        limit: int,
    ) -> list[InventoryItem]:
        """Available EAN-pool units for a shared serial, oldest first (FIFO).

        Used by the Tally sales sync to deduct a quantity of shared-serial
        (EAN-as-serial) units. Only rows flagged ``serial_is_shared`` are
        returned, so the normal unique-serial path is never affected.
        """
        if limit <= 0:
            return []
        normalized = validate_serial_number(serial_number)
        statement = (
            select(InventoryItem)
            .where(
                func.lower(InventoryItem.serial_number) == normalized.lower(),
                InventoryItem.serial_is_shared.is_(True),
                InventoryItem.status == InventoryStatus.AVAILABLE,
                InventoryItem.is_archived.is_(False),
            )
            .order_by(InventoryItem.created_at.asc(), InventoryItem.id.asc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

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
        if await self._has_sale_references(inventory_item.id):
            return "sale references exist"
        if await self._has_audit_references(inventory_item.id):
            return "audit references exist"
        return None

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
                    WHERE inventory_item_id = :inventory_item_id
                       OR (entity_type = 'inventory_item' AND entity_id = :entity_id)
                )
                """),
            {
                "inventory_item_id": inventory_item_id,
                "entity_id": str(inventory_item_id),
            },
        )
        return bool(result.scalar_one())

    async def _table_exists(self, table_name: str) -> bool:
        def check(sync_connection) -> bool:
            inspector = inspect(sync_connection)
            return table_name in inspector.get_table_names(schema=SCHEMA)

        connection = await self._session.connection()
        return await connection.run_sync(check)
