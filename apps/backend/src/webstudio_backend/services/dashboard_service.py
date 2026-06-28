"""Dashboard business logic — operational aggregates only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.repositories.dashboard_repository import (
    DashboardRepository,
    DistributionRow,
)


@dataclass(frozen=True, slots=True)
class DashboardDistribution:
    by_brand: list[DistributionRow]
    by_location: list[DistributionRow]
    by_product_model: list[DistributionRow]
    as_of: datetime


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = DashboardRepository(session)

    async def get_total_available(self) -> int:
        summary = await self._repo.get_inventory_summary()
        return summary.available_inventory

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

    async def _fetch_distribution(
        self,
    ) -> tuple[list[DistributionRow], list[DistributionRow], list[DistributionRow]]:
        return (
            await self._repo.get_distribution_by_brand(),
            await self._repo.get_distribution_by_location(),
            await self._repo.get_distribution_by_product_model(),
        )
