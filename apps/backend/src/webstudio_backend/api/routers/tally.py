"""Tally ERP 9 integration API."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from pydantic import BaseModel

from webstudio_backend.api.dependencies.auth import TallyDashboardDep, TallySyncDep
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.services.tally_dashboard_service import TallyDashboardService
from webstudio_backend.services.tally_sync_service import TallySyncService

router = APIRouter(prefix="/api/v1/integrations/tally", tags=["tally"])

_background_tasks: set[asyncio.Task] = set()


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


class TallySyncTriggerRequest(BaseModel):
    company_name: str | None = None


class TallyConnectionTestResponse(BaseModel):
    connected: bool
    message: str


@router.get("/dashboard")
async def tally_dashboard(
    request: Request,
    current: TallyDashboardDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_dashboard()
    return _envelope(request, data)


@router.get("/status")
async def tally_status(
    request: Request,
    current: TallyDashboardDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_status_summary()
    return _envelope(request, data)


@router.get("/sync-log")
async def tally_sync_log(
    request: Request,
    current: TallyDashboardDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    dashboard = await TallyDashboardService(db_session).build_dashboard()
    return _envelope(request, dashboard["recent_synchronizations"])


@router.post("/connection/test")
async def tally_connection_test(
    request: Request,
    current: TallySyncDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    connected = await TallySyncService(db_session).test_connection()
    return _envelope(
        request,
        TallyConnectionTestResponse(
            connected=connected,
            message="Connected to Tally ERP 9." if connected else "Unable to reach Tally ERP 9.",
        ).model_dump(),
    )


async def _run_background_sync(correlation_id: str, user_id: int | None) -> None:
    from webstudio_backend.infrastructure.database.session import session_scope

    async with session_scope() as session:
        await TallySyncService(session).run_sync(
            correlation_id=correlation_id,
            triggered_by_user_id=user_id,
        )


@router.post("/sync/trigger")
async def tally_sync_trigger(
    request: Request,
    background_tasks: BackgroundTasks,
    current: TallySyncDep,
    db_session=DbSessionDep,
    body: TallySyncTriggerRequest | None = None,
) -> dict:
    _ = body
    sync_service = TallySyncService(db_session)
    if not await sync_service.is_enabled():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tally integration is disabled. Enable it in System Settings.",
        )

    correlation_id = get_correlation_id(request) or str(uuid.uuid4())
    background_tasks.add_task(
        _run_background_sync,
        correlation_id,
        current.user.id,
    )
    return _envelope(
        request,
        {
            "status": "queued",
            "message": "Tally synchronization started in the background.",
            "correlation_id": correlation_id,
        },
    )


@router.post("/sync/retry")
async def tally_sync_retry(
    request: Request,
    background_tasks: BackgroundTasks,
    current: TallySyncDep,
    db_session=DbSessionDep,
) -> dict:
    return await tally_sync_trigger(request, background_tasks, current, db_session)
