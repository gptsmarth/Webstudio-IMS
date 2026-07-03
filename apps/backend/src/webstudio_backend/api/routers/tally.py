"""Tally ERP 9 integration API."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from webstudio_backend.api.dependencies.auth import (
    TallyRetrySyncDep,
    TallyRunSyncDep,
    TallyViewStatusDep,
)
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.integrations.tally.connectivity import TallyHostValidationError
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService
from webstudio_backend.services.tally_dashboard_service import TallyDashboardService
from webstudio_backend.services.tally_production_validation_service import (
    TallyProductionValidationService,
)
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


@router.get("/dashboard")
async def tally_dashboard(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_dashboard()
    return _envelope(request, data)


@router.get("/status")
async def tally_status(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_status_summary()
    return _envelope(request, data)


@router.get("/health")
async def tally_health(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyConnectivityService(db_session).build_health_payload()
    return _envelope(request, data)


@router.get(
    "/production-validation",
    summary="Run M14C production Tally integration validation",
)
async def tally_production_validation(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    service = TallyProductionValidationService(db_session)
    payload = await service.build_production_report(assume_live_tally=True)
    return _envelope(request, payload)


@router.get("/sync/history")
async def tally_sync_history(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_sync_history(
        limit=limit,
        offset=offset,
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return _envelope(request, data)


@router.get("/sync/history/export")
async def tally_sync_history_export(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
    status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    search: str | None = Query(default=None),
) -> Response:
    _ = current
    csv_text = await TallyDashboardService(db_session).export_sync_history_csv(
        status=status,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tally-sync-history.csv"'},
    )


@router.get("/sync-log")
async def tally_sync_log(
    request: Request,
    current: TallyViewStatusDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    data = await TallyDashboardService(db_session).build_sync_history(limit=20)
    return _envelope(request, data)


@router.post("/connection/test")
async def tally_connection_test(
    request: Request,
    current: TallyRunSyncDep,
    db_session=DbSessionDep,
) -> dict:
    _ = current
    service = TallyConnectivityService(db_session)
    try:
        diagnostics = await service.test_connection()
    except TallyHostValidationError as exc:
        return _envelope(
            request,
            {
                "connected": False,
                "reachable": False,
                "message": str(exc),
                "status": "configuration_error",
                "stages": [],
            },
        )
    await db_session.commit()
    payload = TallyConnectivityService.diagnostics_to_api(diagnostics)
    # Backward-compatible fields for existing clients
    payload["connected"] = diagnostics.reachable
    return _envelope(request, payload)


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
    current: TallyRunSyncDep,
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
    current: TallyRetrySyncDep,
    db_session=DbSessionDep,
) -> dict:
    return await tally_sync_trigger(request, background_tasks, current, db_session)
