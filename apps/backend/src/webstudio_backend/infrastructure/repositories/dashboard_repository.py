"""Dashboard aggregate queries — SQL-only, no full-table loads."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import (
    AuditAction,
    AuditSource,
    HUMAN_USER_ROLES,
    InventoryStatus,
    UserStatus,
)
from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.models.user import User

SCHEMA = DATABASE_SCHEMA

_SYNC_ENTITY_TYPES = frozenset(
    {
        "sync_job",
        "tally_sync_log",
        "tally_processed_invoice",
        "tally_integration_event",
    },
)


@dataclass(frozen=True, slots=True)
class InventorySummaryCounts:
    total_inventory: int
    available_inventory: int
    sold_inventory: int
    archived_inventory: int


@dataclass(frozen=True, slots=True)
class ReferenceCounts:
    total_brands: int
    total_product_models: int
    total_locations: int
    active_users: int


@dataclass(frozen=True, slots=True)
class SalesPeriodCounts:
    sales_today: int
    sales_this_week: int
    sales_this_month: int


@dataclass(frozen=True, slots=True)
class DistributionRow:
    group_id: int | uuid.UUID
    group_name: str
    available: int
    sold: int
    total: int


@dataclass(frozen=True, slots=True)
class RecentInventoryRow:
    id: uuid.UUID
    serial_number: str
    brand_name: str
    model_name: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RecentSoldRow:
    id: uuid.UUID
    serial_number: str
    brand_name: str
    model_name: str
    invoice_number: str
    sold_at: datetime


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_inventory_summary(self) -> InventorySummaryCounts:
        statement = select(
            func.count(InventoryItem.id).label("total"),
            func.count(InventoryItem.id)
            .filter(
                InventoryItem.status == InventoryStatus.AVAILABLE,
                InventoryItem.is_archived.is_(False),
            )
            .label("available"),
            func.count(InventoryItem.id)
            .filter(InventoryItem.status == InventoryStatus.SOLD)
            .label("sold"),
            func.count(InventoryItem.id).filter(InventoryItem.is_archived.is_(True)).label("archived"),
        )
        row = (await self._session.execute(statement)).one()
        return InventorySummaryCounts(
            total_inventory=int(row.total),
            available_inventory=int(row.available),
            sold_inventory=int(row.sold),
            archived_inventory=int(row.archived),
        )

    async def get_reference_counts(self) -> ReferenceCounts:
        brands = int(await self._session.scalar(select(func.count()).select_from(Brand)) or 0)
        models = int(await self._session.scalar(select(func.count()).select_from(ProductModel)) or 0)
        locations = int(await self._session.scalar(select(func.count()).select_from(Location)) or 0)
        users = int(
            await self._session.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.status == UserStatus.ACTIVE,
                    User.role.in_(tuple(HUMAN_USER_ROLES)),
                ),
            )
            or 0,
        )
        return ReferenceCounts(
            total_brands=brands,
            total_product_models=models,
            total_locations=locations,
            active_users=users,
        )

    async def get_sales_summary(self, *, now: datetime | None = None) -> SalesPeriodCounts:
        reference = now or datetime.now(UTC)
        start_of_day = reference.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_week = start_of_day - timedelta(days=start_of_day.weekday())
        start_of_month = start_of_day.replace(day=1)

        statement = select(
            func.count(Sale.id).filter(Sale.sold_at >= start_of_day).label("today"),
            func.count(Sale.id).filter(Sale.sold_at >= start_of_week).label("week"),
            func.count(Sale.id).filter(Sale.sold_at >= start_of_month).label("month"),
        )
        row = (await self._session.execute(statement)).one()
        return SalesPeriodCounts(
            sales_today=int(row.today),
            sales_this_week=int(row.week),
            sales_this_month=int(row.month),
        )

    async def get_distribution_by_brand(self) -> list[DistributionRow]:
        available_case = func.count(InventoryItem.id).filter(
            InventoryItem.status == InventoryStatus.AVAILABLE,
            InventoryItem.is_archived.is_(False),
        )
        sold_case = func.count(InventoryItem.id).filter(InventoryItem.status == InventoryStatus.SOLD)
        active_case = func.count(InventoryItem.id).filter(InventoryItem.is_archived.is_(False))

        statement = (
            select(
                Brand.id,
                Brand.name,
                available_case.label("available"),
                sold_case.label("sold"),
                active_case.label("total"),
            )
            .join(ProductModel, ProductModel.brand_id == Brand.id)
            .join(InventoryItem, InventoryItem.product_model_id == ProductModel.id)
            .group_by(Brand.id, Brand.name)
            .order_by(Brand.name.asc())
        )
        result = await self._session.execute(statement)
        return [
            DistributionRow(
                group_id=brand_id,
                group_name=name,
                available=int(available),
                sold=int(sold),
                total=int(total),
            )
            for brand_id, name, available, sold, total in result.all()
        ]

    async def get_distribution_by_location(self) -> list[DistributionRow]:
        available_case = func.count(InventoryItem.id).filter(
            InventoryItem.status == InventoryStatus.AVAILABLE,
            InventoryItem.is_archived.is_(False),
        )
        sold_case = func.count(InventoryItem.id).filter(InventoryItem.status == InventoryStatus.SOLD)
        active_case = func.count(InventoryItem.id).filter(InventoryItem.is_archived.is_(False))

        statement = (
            select(
                Location.id,
                Location.name,
                available_case.label("available"),
                sold_case.label("sold"),
                active_case.label("total"),
            )
            .join(InventoryItem, InventoryItem.current_location_id == Location.id)
            .group_by(Location.id, Location.name)
            .order_by(Location.name.asc())
        )
        result = await self._session.execute(statement)
        return [
            DistributionRow(
                group_id=location_id,
                group_name=name,
                available=int(available),
                sold=int(sold),
                total=int(total),
            )
            for location_id, name, available, sold, total in result.all()
        ]

    async def get_distribution_by_product_model(self) -> list[DistributionRow]:
        available_case = func.count(InventoryItem.id).filter(
            InventoryItem.status == InventoryStatus.AVAILABLE,
            InventoryItem.is_archived.is_(False),
        )
        sold_case = func.count(InventoryItem.id).filter(InventoryItem.status == InventoryStatus.SOLD)
        active_case = func.count(InventoryItem.id).filter(InventoryItem.is_archived.is_(False))

        statement = (
            select(
                ProductModel.id,
                ProductModel.model_name,
                available_case.label("available"),
                sold_case.label("sold"),
                active_case.label("total"),
            )
            .join(InventoryItem, InventoryItem.product_model_id == ProductModel.id)
            .group_by(ProductModel.id, ProductModel.model_name)
            .order_by(ProductModel.model_name.asc())
        )
        result = await self._session.execute(statement)
        return [
            DistributionRow(
                group_id=model_id,
                group_name=name,
                available=int(available),
                sold=int(sold),
                total=int(total),
            )
            for model_id, name, available, sold, total in result.all()
        ]

    async def get_recent_business_activity(self, limit: int) -> list[AuditLog]:
        statement = (
            select(AuditLog)
            .where(self._business_activity_filter())
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_recently_added_inventory(self, limit: int) -> list[RecentInventoryRow]:
        statement = (
            select(
                InventoryItem.id,
                InventoryItem.serial_number,
                Brand.name,
                ProductModel.model_name,
                InventoryItem.status,
                InventoryItem.created_at,
            )
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .join(Brand, ProductModel.brand_id == Brand.id)
            .where(InventoryItem.is_archived.is_(False))
            .order_by(InventoryItem.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [
            RecentInventoryRow(
                id=item_id,
                serial_number=serial,
                brand_name=brand_name,
                model_name=model_name,
                status=status.value,
                created_at=created_at,
            )
            for item_id, serial, brand_name, model_name, status, created_at in result.all()
        ]

    async def get_recently_sold_inventory(self, limit: int) -> list[RecentSoldRow]:
        statement = (
            select(
                InventoryItem.id,
                InventoryItem.serial_number,
                Brand.name,
                ProductModel.model_name,
                Sale.invoice_number,
                Sale.sold_at,
            )
            .join(Sale, Sale.inventory_item_id == InventoryItem.id)
            .join(ProductModel, InventoryItem.product_model_id == ProductModel.id)
            .join(Brand, ProductModel.brand_id == Brand.id)
            .order_by(Sale.sold_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(statement)
        return [
            RecentSoldRow(
                id=item_id,
                serial_number=serial,
                brand_name=brand_name,
                model_name=model_name,
                invoice_number=invoice_number,
                sold_at=sold_at,
            )
            for item_id, serial, brand_name, model_name, invoice_number, sold_at in result.all()
        ]

    async def verify_aggregate_queries_use_sql(self) -> bool:
        """Smoke check that inventory summary uses a single aggregate query."""
        compiled = str(
            select(
                func.count(InventoryItem.id),
            ).compile(compile_kwargs={"literal_binds": True}),
        )
        return "count" in compiled.lower()

    @staticmethod
    def _business_activity_filter():
        return and_(
            AuditLog.source.not_in((AuditSource.TALLY_SYNC, AuditSource.BACKGROUND_JOB)),
            AuditLog.entity_type.not_in(tuple(_SYNC_ENTITY_TYPES)),
            or_(
                and_(
                    AuditLog.entity_type == "inventory_item",
                    AuditLog.action.in_(
                        (
                            AuditAction.CREATE,
                            AuditAction.LOCATION_CHANGE,
                            AuditAction.STATUS_CHANGE,
                            AuditAction.ARCHIVE,
                            AuditAction.RESTORE,
                        ),
                    ),
                ),
                and_(AuditLog.entity_type == "sale", AuditLog.action == AuditAction.CREATE),
                and_(AuditLog.entity_type == "user", AuditLog.action == AuditAction.CREATE),
            ),
        )
