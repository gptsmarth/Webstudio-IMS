"""Dashboard API response schemas — operations center (no KPI analytics)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.repositories.dashboard_repository import DistributionRow
from webstudio_backend.services.dashboard_service import DashboardDistribution


class OperationsDashboardResponse(BaseModel):
    """Minimal operations snapshot — not a BI or KPI dashboard."""

    total_available_inventory: int
    as_of: datetime


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


class DashboardDistributionResponse(BaseModel):
    total_available_inventory: int
    by_brand: list[DistributionGroup]
    by_location: list[DistributionGroup]
    by_product_model: list[DistributionGroup]
    as_of: datetime

    @classmethod
    def from_distribution(
        cls, distribution: DashboardDistribution
    ) -> DashboardDistributionResponse:
        total_available = sum(row.available for row in distribution.by_location)
        return cls(
            total_available_inventory=total_available,
            by_brand=[DistributionGroup.from_row(row) for row in distribution.by_brand],
            by_location=[DistributionGroup.from_row(row) for row in distribution.by_location],
            by_product_model=[
                DistributionGroup.from_row(row) for row in distribution.by_product_model
            ],
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
