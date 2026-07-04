"""Report data access — batched streaming queries, no full-table loads."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import Select, String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    NotificationStatus,
)
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.notification import (
    Notification,
    notification_status,
)
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.pagination import (
    PageParams,
    PageResult,
)
from webstudio_backend.infrastructure.repositories.report_filters import ReportFilters

STREAM_BATCH_SIZE = 500


def _coalesce_serial():
    return func.coalesce(InventoryItem.serial_number, Sale.snapshot_serial_number)


def _coalesce_brand_name():
    return func.coalesce(Brand.name, Sale.snapshot_brand_name)


def _coalesce_model_number():
    return func.coalesce(ProductModel.model_number, Sale.snapshot_model_number)


def _coalesce_model_name():
    return func.coalesce(ProductModel.model_name, Sale.snapshot_model_name)


def _coalesce_location_name():
    return func.coalesce(Location.name, Sale.snapshot_location_name)


def _coalesce_brand_id():
    return func.coalesce(Brand.id, Sale.snapshot_brand_id)


def _coalesce_product_model_id():
    return func.coalesce(ProductModel.id, Sale.snapshot_product_model_id)


def _coalesce_color():
    return func.coalesce(InventoryItem.color, Sale.snapshot_color)


def _coalesce_cpu():
    return func.coalesce(ProductModel.cpu, Sale.snapshot_cpu)


def _coalesce_ram_gb():
    return func.coalesce(ProductModel.ram_gb, Sale.snapshot_ram_gb)


def _coalesce_storage_value():
    return func.coalesce(ProductModel.storage_value, Sale.snapshot_storage_value)


def _coalesce_storage_unit():
    return func.coalesce(
        func.cast(ProductModel.storage_unit, String),
        Sale.snapshot_storage_unit,
    )


def _coalesce_storage_type():
    return func.coalesce(
        func.cast(ProductModel.storage_type, String),
        Sale.snapshot_storage_type,
    )


def _sales_from_clause():
    return (
        Sale.__table__.outerjoin(InventoryItem, Sale.inventory_item_id == InventoryItem.id)
        .outerjoin(ProductModel, InventoryItem.product_model_id == ProductModel.id)
        .outerjoin(
            Brand, or_(ProductModel.brand_id == Brand.id, Sale.snapshot_brand_id == Brand.id)
        )
        .outerjoin(Location, InventoryItem.current_location_id == Location.id)
    )


@dataclass(frozen=True, slots=True)
class InventoryReportRow:
    serial_number: str
    brand_name: str
    model_number: str
    model_name: str
    color: str
    location_name: str
    status: str
    is_archived: bool
    purchase_date: date | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SalesReportRow:
    id: int
    inventory_item_id: uuid.UUID | None
    serial_number: str
    brand_name: str
    model_number: str
    model_name: str
    location_name: str
    invoice_number: str
    customer_name: str | None
    payment_mode: str | None
    sale_amount: float | None
    purchase_price: float | None
    sale_source: str
    sold_at: datetime
    recorded_by_user_id: int | None
    recorded_by_display_name: str | None


@dataclass(frozen=True, slots=True)
class SaleDetailRow(SalesReportRow):
    location_id: int | None
    brand_id: int | None
    product_model_id: uuid.UUID | None
    color: str
    cpu: str
    ram_gb: int | None
    storage_value: str
    storage_unit: str
    storage_type: str
    notes: str | None
    tally_company_name: str | None
    tally_voucher_number: str | None
    printed_invoice_number: str | None
    tally_voucher_guid: str | None
    tally_master_id: str | None
    tally_voucher_type: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class AggregateReportRow:
    group_id: str
    group_name: str
    available: int
    sold: int
    received: int
    reserved: int
    archived: int
    total: int


@dataclass(frozen=True, slots=True)
class AuditReportRow:
    id: uuid.UUID
    entity_type: str
    entity_id: str
    action: str
    source: str
    actor_display_name: str | None
    actor_user_id: int | None
    description: str | None
    serial_number: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class NotificationReportRow:
    id: int
    notification_type: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReportSummary:
    total_rows: int
    by_status: dict[str, int]


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_inventory(self, filters: ReportFilters) -> int:
        statement = select(func.count()).select_from(
            self._inventory_base(filters).subquery(),
        )
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def inventory_summary(self, filters: ReportFilters) -> ReportSummary:
        base = self._inventory_base(filters).subquery()
        statement = select(base.c.status, func.count()).group_by(base.c.status)
        result = await self._session.execute(statement)
        by_status = {status.value: int(count) for status, count in result.all()}
        return ReportSummary(total_rows=sum(by_status.values()), by_status=by_status)

    async def search_inventory(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[InventoryReportRow]:
        statement = self._inventory_select(filters)
        statement = self._apply_inventory_sort(statement, filters)
        return await self._paginate_inventory(statement, page_params)

    async def stream_inventory(
        self,
        filters: ReportFilters,
        *,
        batch_size: int = STREAM_BATCH_SIZE,
    ) -> AsyncIterator[list[InventoryReportRow]]:
        statement = self._inventory_select(filters).order_by(InventoryItem.created_at.desc())
        async for batch in self._stream_rows(statement, batch_size):
            yield [self._map_inventory_row(row) for row in batch]

    async def stream_sales(
        self,
        filters: ReportFilters,
        *,
        batch_size: int = STREAM_BATCH_SIZE,
    ) -> AsyncIterator[list[SalesReportRow]]:
        statement = self._sales_select(filters).order_by(Sale.sold_at.desc())
        async for batch in self._stream_rows(statement, batch_size):
            yield [self._map_sales_row(row) for row in batch]

    async def stream_audit(
        self,
        filters: ReportFilters,
        *,
        batch_size: int = STREAM_BATCH_SIZE,
    ) -> AsyncIterator[list[AuditReportRow]]:
        statement = self._audit_select(filters).order_by(AuditLog.created_at.desc())
        async for batch in self._stream_rows(statement, batch_size):
            yield [self._map_audit_row(row) for row in batch]

    async def stream_notifications(
        self,
        filters: ReportFilters,
        *,
        batch_size: int = STREAM_BATCH_SIZE,
    ) -> AsyncIterator[list[NotificationReportRow]]:
        statement = self._notification_select(filters).order_by(Notification.created_at.desc())
        offset = 0
        while True:
            result = await self._session.execute(statement.limit(batch_size).offset(offset))
            notifications = list(result.scalars().all())
            if not notifications:
                break
            yield [self._map_notification_row(notification) for notification in notifications]
            if len(notifications) < batch_size:
                break
            offset += batch_size

    async def _stream_rows(self, statement, batch_size: int) -> AsyncIterator[list]:
        offset = 0
        while True:
            result = await self._session.execute(statement.limit(batch_size).offset(offset))
            rows = result.all()
            if not rows:
                break
            yield rows
            if len(rows) < batch_size:
                break
            offset += batch_size

    async def count_sales(self, filters: ReportFilters) -> int:
        statement = select(func.count()).select_from(self._sales_base(filters).subquery())
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def search_sales(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[SalesReportRow]:
        statement = self._sales_select(filters)
        statement = self._apply_sales_sort(statement, filters)
        return await self._paginate_sales(statement, page_params)

    async def get_sale_detail_by_id(self, sale_id: int) -> SaleDetailRow | None:
        statement = self._sales_detail_select().where(Sale.id == sale_id)
        result = await self._session.execute(statement)
        row = result.one_or_none()
        if row is None:
            return None
        return self._map_sale_detail_row(row)

    async def aggregate_by_location(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._aggregate(filters, Location.id, Location.name)

    async def aggregate_by_brand(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._aggregate(filters, Brand.id, Brand.name)

    async def aggregate_by_product_model(self, filters: ReportFilters) -> list[AggregateReportRow]:
        return await self._aggregate(filters, ProductModel.id, ProductModel.model_name)

    async def count_audit(self, filters: ReportFilters) -> int:
        statement = select(func.count()).select_from(self._audit_base(filters).subquery())
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def search_audit(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[AuditReportRow]:
        statement = self._audit_select(filters)
        statement = self._apply_audit_sort(statement, filters)
        return await self._paginate_audit(statement, page_params)

    async def count_notifications(self, filters: ReportFilters) -> int:
        statement = select(func.count()).select_from(self._notification_base(filters).subquery())
        result = await self._session.execute(statement)
        return int(result.scalar_one())

    async def search_notifications(
        self,
        filters: ReportFilters,
        page_params: PageParams,
    ) -> PageResult[NotificationReportRow]:
        statement = self._notification_select(filters)
        statement = self._apply_notification_sort(statement, filters)
        return await self._paginate_notifications(statement, page_params)

    def _inventory_base(self, filters: ReportFilters) -> Select:
        statement = (
            select(InventoryItem)
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .join(Brand, ProductModel.brand_id == Brand.id)
            .join(Location, InventoryItem.current_location_id == Location.id)
        )
        return self._apply_inventory_filters(statement, filters)

    def _inventory_select(self, filters: ReportFilters):
        return (
            select(
                InventoryItem.serial_number,
                Brand.name,
                ProductModel.model_number,
                ProductModel.model_name,
                InventoryItem.color,
                Location.name,
                InventoryItem.status,
                InventoryItem.is_archived,
                InventoryItem.purchase_date,
                InventoryItem.created_at,
            )
            .select_from(
                InventoryItem.__table__.join(
                    ProductModel, InventoryItem.product_model_id == ProductModel.id
                )
                .join(Brand, ProductModel.brand_id == Brand.id)
                .join(Location, InventoryItem.current_location_id == Location.id),
            )
            .where(*self._inventory_where_clauses(filters))
        )

    def _inventory_where_clauses(self, filters: ReportFilters) -> list:
        clauses = []
        if filters.brand_id is not None:
            clauses.append(Brand.id == filters.brand_id)
        if filters.location_id is not None:
            clauses.append(Location.id == filters.location_id)
        if filters.location_type is not None:
            clauses.append(Location.location_type == filters.location_type)
        if filters.product_model_id is not None:
            clauses.append(ProductModel.id == filters.product_model_id)
        if filters.inventory_status is not None:
            clauses.append(InventoryItem.status == filters.inventory_status)
        if filters.is_archived is not None:
            clauses.append(InventoryItem.is_archived.is_(filters.is_archived))
        if filters.serial_number is not None and filters.serial_number.strip():
            clauses.append(InventoryItem.serial_number.ilike(f"%{filters.serial_number.strip()}%"))
        if filters.color is not None and filters.color.strip():
            clauses.append(InventoryItem.color.ilike(f"%{filters.color.strip()}%"))
        if filters.purchase_date_from is not None:
            clauses.append(InventoryItem.purchase_date >= filters.purchase_date_from)
        if filters.purchase_date_to is not None:
            clauses.append(InventoryItem.purchase_date <= filters.purchase_date_to)
        if filters.date_from is not None:
            clauses.append(InventoryItem.created_at >= filters.date_from)
        if filters.date_to is not None:
            clauses.append(InventoryItem.created_at <= filters.date_to)
        if filters.search is not None and filters.search.strip():
            term = filters.search.strip()
            clauses.append(
                or_(
                    InventoryItem.serial_number.ilike(f"%{term}%"),
                    Brand.name.ilike(f"%{term}%"),
                    ProductModel.model_number.ilike(f"%{term}%"),
                    ProductModel.model_name.ilike(f"%{term}%"),
                    Location.name.ilike(f"%{term}%"),
                    InventoryItem.color.ilike(f"%{term}%"),
                ),
            )
        return clauses

    def _apply_inventory_sort(self, statement, filters: ReportFilters):
        direction = (filters.sort_direction or "desc").lower()
        descending = direction != "asc"
        field = filters.sort_field or "created_at"
        column_map = {
            "serial_number": InventoryItem.serial_number,
            "status": InventoryItem.status,
            "color": InventoryItem.color,
            "purchase_date": InventoryItem.purchase_date,
            "created_at": InventoryItem.created_at,
            "brand_name": Brand.name,
            "location_name": Location.name,
            "model_name": ProductModel.model_name,
        }
        column = column_map.get(field, InventoryItem.created_at)
        return statement.order_by(column.desc() if descending else column.asc())

    def _apply_inventory_filters(self, statement: Select, filters: ReportFilters) -> Select:
        clauses = self._inventory_where_clauses(filters)
        if clauses:
            statement = statement.where(*clauses)
        return statement

    def _sales_base(self, filters: ReportFilters) -> Select:
        statement = select(Sale).select_from(_sales_from_clause())
        return self._apply_sales_filters(statement, filters)

    def _sales_select(self, filters: ReportFilters):
        return (
            select(
                Sale.id,
                Sale.inventory_item_id,
                _coalesce_serial(),
                _coalesce_brand_name(),
                _coalesce_model_number(),
                _coalesce_model_name(),
                _coalesce_location_name(),
                Sale.invoice_number,
                Sale.customer_name,
                Sale.payment_mode,
                Sale.sale_amount,
                Sale.snapshot_purchase_price,
                Sale.sale_source,
                Sale.sold_at,
                Sale.recorded_by_user_id,
                User.display_name,
            )
            .select_from(
                _sales_from_clause().outerjoin(User, Sale.recorded_by_user_id == User.id),
            )
            .where(*self._sales_where_clauses(filters))
        )

    def _sales_detail_select(self):
        return select(
            Sale.id,
            Sale.inventory_item_id,
            _coalesce_serial(),
            _coalesce_brand_id(),
            _coalesce_brand_name(),
            _coalesce_product_model_id(),
            _coalesce_model_number(),
            _coalesce_model_name(),
            func.coalesce(Location.id, Sale.mapped_location_id),
            _coalesce_location_name(),
            Sale.invoice_number,
            Sale.customer_name,
            Sale.payment_mode,
            Sale.sale_amount,
            Sale.snapshot_purchase_price,
            Sale.sale_source,
            Sale.sold_at,
            Sale.recorded_by_user_id,
            User.display_name,
            _coalesce_color(),
            _coalesce_cpu(),
            _coalesce_ram_gb(),
            _coalesce_storage_value(),
            _coalesce_storage_unit(),
            _coalesce_storage_type(),
            Sale.notes,
            Sale.tally_company_name,
            Sale.tally_voucher_number,
            Sale.printed_invoice_number,
            Sale.tally_voucher_guid,
            Sale.tally_master_id,
            Sale.tally_voucher_type,
            Sale.created_at,
        ).select_from(
            _sales_from_clause().outerjoin(User, Sale.recorded_by_user_id == User.id),
        )

    def _sales_where_clauses(self, filters: ReportFilters) -> list:
        clauses = []
        if filters.brand_id is not None:
            clauses.append(
                or_(
                    Brand.id == filters.brand_id,
                    Sale.snapshot_brand_id == filters.brand_id,
                ),
            )
        if filters.location_id is not None:
            clauses.append(Location.id == filters.location_id)
        if filters.location_type is not None:
            clauses.append(Location.location_type == filters.location_type)
        if filters.product_model_id is not None:
            clauses.append(
                or_(
                    ProductModel.id == filters.product_model_id,
                    Sale.snapshot_product_model_id == filters.product_model_id,
                ),
            )
        if filters.user_id is not None:
            clauses.append(Sale.recorded_by_user_id == filters.user_id)
        if filters.date_from is not None:
            clauses.append(Sale.sold_at >= filters.date_from)
        if filters.date_to is not None:
            clauses.append(Sale.sold_at <= filters.date_to)
        if filters.invoice_number is not None:
            clauses.append(Sale.invoice_number.ilike(f"%{filters.invoice_number.strip()}%"))
        if filters.customer_name is not None:
            clauses.append(Sale.customer_name.ilike(f"%{filters.customer_name.strip()}%"))
        if filters.payment_mode is not None:
            clauses.append(Sale.payment_mode.ilike(f"%{filters.payment_mode.strip()}%"))
        if filters.sale_source is not None:
            clauses.append(Sale.sale_source == filters.sale_source)
        if filters.serial_number is not None and filters.serial_number.strip():
            serial_term = f"%{filters.serial_number.strip()}%"
            clauses.append(
                or_(
                    InventoryItem.serial_number.ilike(serial_term),
                    Sale.snapshot_serial_number.ilike(serial_term),
                ),
            )
        if filters.search is not None:
            term = filters.search.strip()
            if term:
                clauses.append(
                    or_(
                        Sale.invoice_number.ilike(f"%{term}%"),
                        Sale.customer_name.ilike(f"%{term}%"),
                        InventoryItem.serial_number.ilike(f"{term}%"),
                        Sale.snapshot_serial_number.ilike(f"{term}%"),
                        Brand.name.ilike(f"%{term}%"),
                        Sale.snapshot_brand_name.ilike(f"%{term}%"),
                        ProductModel.model_name.ilike(f"%{term}%"),
                        Sale.snapshot_model_name.ilike(f"%{term}%"),
                        Location.name.ilike(f"%{term}%"),
                        Sale.snapshot_location_name.ilike(f"%{term}%"),
                    ),
                )
        return clauses

    def _apply_sales_sort(self, statement, filters: ReportFilters):
        direction = (filters.sort_direction or "desc").lower()
        descending = direction != "asc"
        field = filters.sort_field or "sold_at"
        column_map = {
            "sold_at": Sale.sold_at,
            "invoice_number": Sale.invoice_number,
            "customer_name": Sale.customer_name,
            "serial_number": _coalesce_serial(),
            "brand_name": _coalesce_brand_name(),
            "model_name": _coalesce_model_name(),
            "location_name": _coalesce_location_name(),
            "payment_mode": Sale.payment_mode,
            "sale_source": Sale.sale_source,
        }
        column = column_map.get(field, Sale.sold_at)
        return statement.order_by(column.desc() if descending else column.asc())

    def _apply_sales_filters(self, statement: Select, filters: ReportFilters) -> Select:
        clauses = self._sales_where_clauses(filters)
        if clauses:
            statement = statement.where(*clauses)
        return statement

    def _audit_base(self, filters: ReportFilters) -> Select:
        statement = select(AuditLog).outerjoin(
            InventoryItem,
            AuditLog.inventory_item_id == InventoryItem.id,
        )
        return self._apply_audit_filters(statement, filters)

    def _audit_select(self, filters: ReportFilters):
        return (
            select(
                AuditLog.id,
                AuditLog.entity_type,
                AuditLog.entity_id,
                AuditLog.action,
                AuditLog.source,
                AuditLog.actor_display_name,
                AuditLog.actor_user_id,
                AuditLog.description,
                InventoryItem.serial_number,
                AuditLog.created_at,
            )
            .select_from(
                AuditLog.__table__.outerjoin(
                    InventoryItem,
                    AuditLog.inventory_item_id == InventoryItem.id,
                ),
            )
            .where(*self._audit_where_clauses(filters))
        )

    def _audit_where_clauses(self, filters: ReportFilters) -> list:
        clauses = []
        if filters.user_id is not None:
            clauses.append(AuditLog.actor_user_id == filters.user_id)
        if filters.actor_role is not None and filters.actor_role.strip():
            clauses.append(AuditLog.actor_role == filters.actor_role.strip())
        if filters.audit_action is not None:
            clauses.append(AuditLog.action == filters.audit_action)
        if filters.audit_source is not None:
            clauses.append(AuditLog.source == filters.audit_source)
        if filters.date_from is not None:
            clauses.append(AuditLog.created_at >= filters.date_from)
        if filters.date_to is not None:
            clauses.append(AuditLog.created_at <= filters.date_to)
        if filters.serial_number is not None and filters.serial_number.strip():
            clauses.append(InventoryItem.serial_number.ilike(f"%{filters.serial_number.strip()}%"))
        if filters.brand_id is not None or filters.product_model_id is not None:
            statement_brand = select(InventoryItem.id).join(
                ProductModel,
                InventoryItem.product_model_id == ProductModel.id,
            )
            if filters.brand_id is not None:
                statement_brand = statement_brand.where(ProductModel.brand_id == filters.brand_id)
            if filters.product_model_id is not None:
                statement_brand = statement_brand.where(ProductModel.id == filters.product_model_id)
            clauses.append(
                or_(
                    AuditLog.inventory_item_id.in_(statement_brand),
                    AuditLog.entity_type == "product_model",
                ),
            )
        if filters.location_id is not None:
            location_items = select(InventoryItem.id).where(
                InventoryItem.current_location_id == filters.location_id,
            )
            clauses.append(AuditLog.inventory_item_id.in_(location_items))
        if filters.search is not None and filters.search.strip():
            term = filters.search.strip()
            clauses.append(
                or_(
                    AuditLog.description.ilike(f"%{term}%"),
                    AuditLog.actor_display_name.ilike(f"%{term}%"),
                    InventoryItem.serial_number.ilike(f"%{term}%"),
                ),
            )
        if filters.security_only:
            from webstudio_backend.services.audit_log_presenter import SECURITY_ENTITY_TYPES

            clauses.append(
                or_(
                    AuditLog.entity_type.in_(tuple(SECURITY_ENTITY_TYPES)),
                    AuditLog.new_value["security_event"].astext.isnot(None),
                ),
            )
        if filters.audit_severity is not None:
            clauses.append(AuditLog.new_value["severity"].astext == filters.audit_severity)
        return clauses

    def _apply_audit_sort(self, statement, filters: ReportFilters):
        direction = (filters.sort_direction or "desc").lower()
        descending = direction != "asc"
        field = filters.sort_field or "created_at"
        column_map = {
            "created_at": AuditLog.created_at,
            "action": AuditLog.action,
            "source": AuditLog.source,
            "serial_number": InventoryItem.serial_number,
            "actor_display_name": AuditLog.actor_display_name,
        }
        column = column_map.get(field, AuditLog.created_at)
        return statement.order_by(column.desc() if descending else column.asc())

    def _apply_audit_filters(self, statement: Select, filters: ReportFilters) -> Select:
        clauses = self._audit_where_clauses(filters)
        if clauses:
            statement = statement.where(*clauses)
        return statement

    def _notification_base(self, filters: ReportFilters) -> Select:
        return self._apply_notification_filters(select(Notification), filters)

    def _notification_select(self, filters: ReportFilters):
        return select(Notification).where(*self._notification_where_clauses(filters))

    def _notification_where_clauses(self, filters: ReportFilters) -> list:
        clauses = []
        if filters.date_from is not None:
            clauses.append(Notification.created_at >= filters.date_from)
        if filters.date_to is not None:
            clauses.append(Notification.created_at <= filters.date_to)
        if filters.user_id is not None:
            clauses.append(
                or_(
                    Notification.created_by_user_id == filters.user_id,
                    Notification.resolved_by_user_id == filters.user_id,
                ),
            )
        if filters.notification_status is NotificationStatus.UNREAD:
            clauses.extend(
                [
                    Notification.is_read.is_(False),
                    Notification.is_resolved.is_(False),
                ],
            )
        elif filters.notification_status is NotificationStatus.READ:
            clauses.extend(
                [
                    Notification.is_read.is_(True),
                    Notification.is_resolved.is_(False),
                ],
            )
        elif filters.notification_status is NotificationStatus.RESOLVED:
            clauses.append(Notification.is_resolved.is_(True))
        if filters.notification_type is not None:
            clauses.append(Notification.notification_type == filters.notification_type)
        if filters.notification_category is not None:
            clauses.append(Notification.category == filters.notification_category)
        if filters.search is not None and filters.search.strip():
            term = filters.search.strip()
            clauses.append(
                or_(
                    Notification.title.ilike(f"%{term}%"),
                    Notification.description.ilike(f"%{term}%"),
                ),
            )
        return clauses

    def _apply_notification_sort(self, statement, filters: ReportFilters):
        direction = (filters.sort_direction or "desc").lower()
        descending = direction != "asc"
        field = filters.sort_field or "created_at"
        column_map = {
            "created_at": Notification.created_at,
            "notification_type": Notification.notification_type,
            "status": Notification.created_at,
            "title": Notification.title,
            "severity": Notification.severity,
        }
        column = column_map.get(field, Notification.created_at)
        return statement.order_by(column.desc() if descending else column.asc())

    def _apply_notification_filters(self, statement: Select, filters: ReportFilters) -> Select:
        clauses = self._notification_where_clauses(filters)
        if clauses:
            statement = statement.where(*clauses)
        return statement

    async def _aggregate(
        self,
        filters: ReportFilters,
        group_id_col,
        group_name_col,
    ) -> list[AggregateReportRow]:
        available = func.count().filter(
            InventoryItem.status == InventoryStatus.AVAILABLE,
            InventoryItem.is_archived.is_(False),
        )
        sold = func.count().filter(InventoryItem.status == InventoryStatus.SOLD)
        received = func.count().filter(InventoryItem.status == InventoryStatus.RECEIVED)
        reserved = func.count().filter(InventoryItem.status == InventoryStatus.RESERVED)
        archived = func.count().filter(InventoryItem.is_archived.is_(True))
        total = func.count()

        statement = (
            select(
                group_id_col,
                group_name_col,
                available,
                sold,
                received,
                reserved,
                archived,
                total,
            )
            .select_from(
                InventoryItem.__table__.join(
                    ProductModel, InventoryItem.product_model_id == ProductModel.id
                )
                .join(Brand, ProductModel.brand_id == Brand.id)
                .join(Location, InventoryItem.current_location_id == Location.id),
            )
            .where(*self._inventory_where_clauses(filters))
            .group_by(group_id_col, group_name_col)
            .order_by(group_name_col.asc())
        )
        result = await self._session.execute(statement)
        return [
            AggregateReportRow(
                group_id=str(group_id),
                group_name=name,
                available=int(avail),
                sold=int(sold_count),
                received=int(recv),
                reserved=int(resv),
                archived=int(arch),
                total=int(tot),
            )
            for group_id, name, avail, sold_count, recv, resv, arch, tot in result.all()
        ]

    async def _paginate_inventory(
        self,
        statement,
        page_params: PageParams,
    ) -> PageResult[InventoryReportRow]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total_result = await self._session.execute(count_statement)
        total_items = int(total_result.scalar_one())
        paginated = statement.limit(page_params.page_size).offset(page_params.offset)
        result = await self._session.execute(paginated)
        items = [self._map_inventory_row(row) for row in result.all()]
        return PageResult(
            items=items,
            total_items=total_items,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def _paginate_sales(
        self, statement, page_params: PageParams
    ) -> PageResult[SalesReportRow]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total_result = await self._session.execute(count_statement)
        total_items = int(total_result.scalar_one())
        paginated = statement.limit(page_params.page_size).offset(page_params.offset)
        result = await self._session.execute(paginated)
        items = [self._map_sales_row(row) for row in result.all()]
        return PageResult(
            items=items,
            total_items=total_items,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def _paginate_audit(
        self, statement, page_params: PageParams
    ) -> PageResult[AuditReportRow]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total_result = await self._session.execute(count_statement)
        total_items = int(total_result.scalar_one())
        paginated = statement.limit(page_params.page_size).offset(page_params.offset)
        result = await self._session.execute(paginated)
        items = [self._map_audit_row(row) for row in result.all()]
        return PageResult(
            items=items,
            total_items=total_items,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    async def _paginate_notifications(
        self,
        statement,
        page_params: PageParams,
    ) -> PageResult[NotificationReportRow]:
        count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total_result = await self._session.execute(count_statement)
        total_items = int(total_result.scalar_one())
        paginated = statement.limit(page_params.page_size).offset(page_params.offset)
        result = await self._session.execute(paginated)
        items = [self._map_notification_row(row) for row in result.scalars().all()]
        return PageResult(
            items=items,
            total_items=total_items,
            page=page_params.page,
            page_size=page_params.page_size,
        )

    @staticmethod
    def _map_inventory_row(row) -> InventoryReportRow:
        (
            serial,
            brand_name,
            model_number,
            model_name,
            color,
            location_name,
            status,
            is_archived,
            purchase_date,
            created_at,
        ) = row
        return InventoryReportRow(
            serial_number=serial,
            brand_name=brand_name,
            model_number=model_number,
            model_name=model_name,
            color=color,
            location_name=location_name,
            status=status.value,
            is_archived=is_archived,
            purchase_date=purchase_date,
            created_at=created_at,
        )

    @staticmethod
    def _enum_label(value) -> str:
        if value is None:
            return ""
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _map_sales_row(row) -> SalesReportRow:
        (
            sale_id,
            inventory_item_id,
            serial,
            brand_name,
            model_number,
            model_name,
            location_name,
            invoice_number,
            customer_name,
            payment_mode,
            sale_amount,
            purchase_price,
            sale_source,
            sold_at,
            recorded_by_user_id,
            recorded_by_display_name,
        ) = row
        return SalesReportRow(
            id=sale_id,
            inventory_item_id=inventory_item_id,
            serial_number=serial,
            brand_name=brand_name,
            model_number=model_number,
            model_name=model_name,
            location_name=location_name,
            invoice_number=invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            sale_amount=float(sale_amount) if sale_amount is not None else None,
            purchase_price=float(purchase_price) if purchase_price is not None else None,
            sale_source=sale_source.value,
            sold_at=sold_at,
            recorded_by_user_id=recorded_by_user_id,
            recorded_by_display_name=recorded_by_display_name,
        )

    @staticmethod
    def _map_sale_detail_row(row) -> SaleDetailRow:
        (
            sale_id,
            inventory_item_id,
            serial,
            brand_id,
            brand_name,
            product_model_id,
            model_number,
            model_name,
            location_id,
            location_name,
            invoice_number,
            customer_name,
            payment_mode,
            sale_amount,
            purchase_price,
            sale_source,
            sold_at,
            recorded_by_user_id,
            recorded_by_display_name,
            color,
            cpu,
            ram_gb,
            storage_value,
            storage_unit,
            storage_type,
            notes,
            tally_company_name,
            tally_voucher_number,
            printed_invoice_number,
            tally_voucher_guid,
            tally_master_id,
            tally_voucher_type,
            created_at,
        ) = row
        return SaleDetailRow(
            id=sale_id,
            inventory_item_id=inventory_item_id,
            serial_number=serial,
            brand_name=brand_name,
            model_number=model_number,
            model_name=model_name,
            location_name=location_name,
            invoice_number=invoice_number,
            customer_name=customer_name,
            payment_mode=payment_mode,
            sale_amount=float(sale_amount) if sale_amount is not None else None,
            purchase_price=float(purchase_price) if purchase_price is not None else None,
            sale_source=sale_source.value,
            sold_at=sold_at,
            recorded_by_user_id=recorded_by_user_id,
            recorded_by_display_name=recorded_by_display_name,
            location_id=location_id,
            brand_id=brand_id,
            product_model_id=product_model_id,
            color=color or "",
            cpu=cpu or "",
            ram_gb=ram_gb,
            storage_value=str(storage_value) if storage_value is not None else "",
            storage_unit=ReportRepository._enum_label(storage_unit),
            storage_type=ReportRepository._enum_label(storage_type),
            notes=notes,
            tally_company_name=tally_company_name,
            tally_voucher_number=tally_voucher_number,
            printed_invoice_number=printed_invoice_number,
            tally_voucher_guid=tally_voucher_guid,
            tally_master_id=tally_master_id,
            tally_voucher_type=tally_voucher_type,
            created_at=created_at,
        )

    @staticmethod
    def _map_audit_row(row) -> AuditReportRow:
        (
            log_id,
            entity_type,
            entity_id,
            action,
            source,
            actor_display_name,
            actor_user_id,
            description,
            serial_number,
            created_at,
        ) = row
        return AuditReportRow(
            id=log_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action.value,
            source=source.value,
            actor_display_name=actor_display_name,
            actor_user_id=actor_user_id,
            description=description,
            serial_number=serial_number,
            created_at=created_at,
        )

    @staticmethod
    def _map_notification_row(row) -> NotificationReportRow:
        if isinstance(row, Notification):
            notification = row
        else:
            notification = row[0]
        return NotificationReportRow(
            id=notification.id,
            notification_type=notification.notification_type.value,
            title=notification.title,
            description=notification.message,
            category=notification.category.value,
            severity=notification.severity.value,
            status=notification_status(notification).value,
            created_at=notification.created_at,
            resolved_at=notification.resolved_at,
        )
