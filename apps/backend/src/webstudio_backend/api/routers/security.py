"""Security monitoring and session administration API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import SettingsViewDep
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import DbSessionDep, get_app_settings
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.repositories.report_filters import (
    ExportFormat,
    ReportFilters,
    ReportType,
)
from webstudio_backend.services.report_service import ReportService
from webstudio_backend.services.security_service import SecurityService

router = APIRouter(prefix="/api/v1/security", tags=["security"])


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


@router.get("/dashboard")
async def security_dashboard(
    request: Request,
    current: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    payload = await SecurityService(db_session, settings).get_dashboard(viewer=current.user)
    return _envelope(request, payload)


@router.get("/export")
async def export_security_events(
    current: SettingsViewDep,
    db_session: AsyncSession = DbSessionDep,
    format: ExportFormat = Query(default=ExportFormat.XLSX, alias="format"),
    audit_severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
) -> Response:
    del current
    filters = ReportFilters(security_only=True, audit_severity=audit_severity)
    content, media_type, filename = await ReportService(db_session).export_report(
        report_type=ReportType.AUDIT,
        export_format=format,
        filters=filters,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
