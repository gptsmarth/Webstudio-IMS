"""Dashboard API response schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.repositories.dashboard_repository import (
    DistributionRow,
    RecentInventoryRow,
    RecentSoldRow,
    WarrantyExpiringRow,
)
from webstudio_backend.services.dashboard_service import (
    DashboardDistribution,
    DashboardOverview,
)


class InventorySummary(BaseModel):
    total_inventory: int
    available_inventory: int
    sold_inventory: int
    archived_inventory: int
    total_brands: int
    total_product_models: int
    total_locations: int
    active_users: int


class SalesSummary(BaseModel):
    sales_today: int
    sales_this_week: int
    sales_this_month: int


class DistributionGroup(BaseModel):
    id: str
    name: str
    available: int
    sold: int
    total: int

    @classmethod
    def from_row(cls, row: DistributionRow) -> DistributionGroup:
        return cls(
            id=str(row.group_id),
            name=row.group_name,
            available=row.available,
            sold=row.sold,
            total=row.total,
        )


class RecentInventoryInsight(BaseModel):
    id: uuid.UUID
    serial_number: str
    brand_name: str
    model_name: str
    status: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: RecentInventoryRow) -> RecentInventoryInsight:
        return cls(
            id=row.id,
            serial_number=row.serial_number,
            brand_name=row.brand_name,
            model_name=row.model_name,
            status=row.status,
            created_at=row.created_at,
        )


class RecentSoldInsight(BaseModel):
    id: uuid.UUID
    serial_number: str
    brand_name: str
    model_name: str
    invoice_number: str
    sold_at: datetime

    @classmethod
    def from_row(cls, row: RecentSoldRow) -> RecentSoldInsight:
        return cls(
            id=row.id,
            serial_number=row.serial_number,
            brand_name=row.brand_name,
            model_name=row.model_name,
            invoice_number=row.invoice_number,
            sold_at=row.sold_at,
        )


class WarrantyExpiringInsight(BaseModel):
    id: uuid.UUID
    serial_number: str
    brand_name: str
    model_name: str
    warranty_expiry: date
    days_remaining: int

    @classmethod
    def from_row(cls, row: WarrantyExpiringRow) -> WarrantyExpiringInsight:
        return cls(
            id=row.id,
            serial_number=row.serial_number,
            brand_name=row.brand_name,
            model_name=row.model_name,
            warranty_expiry=row.warranty_expiry,
            days_remaining=row.days_remaining,
        )


class DashboardInsights(BaseModel):
    archived_inventory_count: int
    recently_added_inventory: list[RecentInventoryInsight]
    recently_sold_inventory: list[RecentSoldInsight]
    warranty_expiring_soon: list[WarrantyExpiringInsight]
    warranty_threshold_days: int


class DashboardResponse(BaseModel):
    summary: InventorySummary
    sales_summary: SalesSummary
    insights: DashboardInsights
    as_of: datetime

    @classmethod
    def from_overview(
        cls,
        overview: DashboardOverview,
        *,
        warranty_threshold_days: int,
    ) -> DashboardResponse:
        return cls(
            summary=InventorySummary(
                total_inventory=overview.summary.total_inventory,
                available_inventory=overview.summary.available_inventory,
                sold_inventory=overview.summary.sold_inventory,
                archived_inventory=overview.summary.archived_inventory,
                total_brands=overview.reference_counts.total_brands,
                total_product_models=overview.reference_counts.total_product_models,
                total_locations=overview.reference_counts.total_locations,
                active_users=overview.reference_counts.active_users,
            ),
            sales_summary=SalesSummary(
                sales_today=overview.sales_summary.sales_today,
                sales_this_week=overview.sales_summary.sales_this_week,
                sales_this_month=overview.sales_summary.sales_this_month,
            ),
            insights=DashboardInsights(
                archived_inventory_count=overview.insights.archived_inventory_count,
                recently_added_inventory=[
                    RecentInventoryInsight.from_row(row)
                    for row in overview.insights.recently_added_inventory
                ],
                recently_sold_inventory=[
                    RecentSoldInsight.from_row(row) for row in overview.insights.recently_sold_inventory
                ],
                warranty_expiring_soon=[
                    WarrantyExpiringInsight.from_row(row)
                    for row in overview.insights.warranty_expiring_soon
                ],
                warranty_threshold_days=warranty_threshold_days,
            ),
            as_of=overview.as_of,
        )


class DashboardDistributionResponse(BaseModel):
    by_brand: list[DistributionGroup]
    by_location: list[DistributionGroup]
    by_product_model: list[DistributionGroup]
    as_of: datetime

    @classmethod
    def from_distribution(cls, distribution: DashboardDistribution) -> DashboardDistributionResponse:
        return cls(
            by_brand=[DistributionGroup.from_row(row) for row in distribution.by_brand],
            by_location=[DistributionGroup.from_row(row) for row in distribution.by_location],
            by_product_model=[DistributionGroup.from_row(row) for row in distribution.by_product_model],
            as_of=distribution.as_of,
        )


class RecentActivityEntry(BaseModel):
    id: uuid.UUID
    activity_type: str
    entity_type: str
    entity_id: str
    description: str | None
    actor_display_name: str | None
    actor_role: str | None
    created_at: datetime

    @classmethod
    def from_audit_log(cls, entry: AuditLog) -> RecentActivityEntry:
        return cls(
            id=entry.id,
            activity_type=_activity_type(entry),
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            description=entry.description,
            actor_display_name=entry.actor_display_name,
            actor_role=entry.actor_role,
            created_at=entry.created_at,
        )


def _activity_type(entry: AuditLog) -> str:
    if entry.entity_type == "inventory_item" and entry.action.value == "CREATE":
        return "inventory_created"
    if entry.entity_type == "sale" and entry.action.value == "CREATE":
        return "manual_sale"
    if entry.action.value == "LOCATION_CHANGE":
        return "location_transfer"
    if entry.entity_type == "user" and entry.action.value == "CREATE":
        return "user_created"
    if entry.action.value == "STATUS_CHANGE":
        return "status_change"
    if entry.action.value == "ARCHIVE":
        return "inventory_archived"
    if entry.action.value == "RESTORE":
        return "inventory_restored"
    return entry.action.value.lower()
