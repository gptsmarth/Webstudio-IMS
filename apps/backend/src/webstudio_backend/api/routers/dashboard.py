"""Dashboard API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.schemas.dashboard import (
    DashboardDistributionResponse,
    DashboardResponse,
    RecentActivityEntry,
)
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

DashboardReadDep = Annotated[AuthenticatedUser, Depends(require_permission("dashboard:read"))]


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


@router.get("")
async def get_dashboard(
    request: Request,
    current: DashboardReadDep,
    db_session: AsyncSession = DbSessionDep,
    insights_limit: int = Query(default=10, ge=1, le=50),
    warranty_threshold_days: int = Query(default=30, ge=1, le=365),
) -> dict:
    del current
    overview = await DashboardService(db_session).get_overview(
        insights_limit=insights_limit,
        warranty_threshold_days=warranty_threshold_days,
    )
    response = DashboardResponse.from_overview(
        overview,
        warranty_threshold_days=warranty_threshold_days,
    )
    return _envelope(request, response.model_dump())


@router.get("/recent-activity")
async def get_recent_activity(
    request: Request,
    current: DashboardReadDep,
    db_session: AsyncSession = DbSessionDep,
    limit: int = Query(default=20, ge=1, le=50),
) -> dict:
    del current
    entries = await DashboardService(db_session).get_recent_activity(limit)
    return _envelope(
        request,
        [RecentActivityEntry.from_audit_log(entry).model_dump() for entry in entries],
    )


@router.get("/distribution")
async def get_distribution(
    request: Request,
    current: DashboardReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    distribution = await DashboardService(db_session).get_distribution()
    return _envelope(request, DashboardDistributionResponse.from_distribution(distribution).model_dump())
