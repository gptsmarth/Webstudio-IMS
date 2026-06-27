"""Dashboard business logic — aggregates via DashboardRepository only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.repositories.dashboard_repository import (
    DashboardRepository,
    DistributionRow,
    InventorySummaryCounts,
    RecentInventoryRow,
    RecentSoldRow,
    ReferenceCounts,
    SalesPeriodCounts,
    WarrantyExpiringRow,
)


@dataclass(frozen=True, slots=True)
class DashboardInsights:
    archived_inventory_count: int
    recently_added_inventory: list[RecentInventoryRow]
    recently_sold_inventory: list[RecentSoldRow]
    warranty_expiring_soon: list[WarrantyExpiringRow]


@dataclass(frozen=True, slots=True)
class DashboardOverview:
    summary: InventorySummaryCounts
    reference_counts: ReferenceCounts
    sales_summary: SalesPeriodCounts
    insights: DashboardInsights
    as_of: datetime


@dataclass(frozen=True, slots=True)
class DashboardDistribution:
    by_brand: list[DistributionRow]
    by_location: list[DistributionRow]
    by_product_model: list[DistributionRow]
    as_of: datetime


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DashboardRepository(session)

    async def get_overview(
        self,
        *,
        insights_limit: int = 10,
        warranty_threshold_days: int = 30,
    ) -> DashboardOverview:
        summary = await self._repo.get_inventory_summary()
        reference_counts = await self._repo.get_reference_counts()
        sales_summary = await self._repo.get_sales_summary()
        insights = await self._build_insights(
            summary.archived_inventory,
            insights_limit=insights_limit,
            warranty_threshold_days=warranty_threshold_days,
        )
        return DashboardOverview(
            summary=summary,
            reference_counts=reference_counts,
            sales_summary=sales_summary,
            insights=insights,
            as_of=datetime.now(UTC),
        )

    async def get_distribution(self) -> DashboardDistribution:
        by_brand, by_location, by_model = await self._fetch_distribution()
        return DashboardDistribution(
            by_brand=by_brand,
            by_location=by_location,
            by_product_model=by_model,
            as_of=datetime.now(UTC),
        )

    async def get_recent_activity(self, limit: int = 20) -> list[AuditLog]:
        return await self._repo.get_recent_business_activity(limit)

    async def _build_insights(
        self,
        archived_count: int,
        *,
        insights_limit: int,
        warranty_threshold_days: int,
    ) -> DashboardInsights:
        return DashboardInsights(
            archived_inventory_count=archived_count,
            recently_added_inventory=await self._repo.get_recently_added_inventory(insights_limit),
            recently_sold_inventory=await self._repo.get_recently_sold_inventory(insights_limit),
            warranty_expiring_soon=await self._repo.get_warranty_expiring_soon(
                threshold_days=warranty_threshold_days,
                limit=insights_limit,
            ),
        )

    async def _fetch_distribution(
        self,
    ) -> tuple[list[DistributionRow], list[DistributionRow], list[DistributionRow]]:
        return (
            await self._repo.get_distribution_by_brand(),
            await self._repo.get_distribution_by_location(),
            await self._repo.get_distribution_by_product_model(),
        )
