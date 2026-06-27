"""Reports and export API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.schemas.report import (
    AuditReportResponse,
    AuditReportRowResponse,
    InventoryReportResponse,
    InventoryReportRowResponse,
    NotificationReportResponse,
    NotificationReportRowResponse,
    ReportFiltersApplied,
    SalesReportResponse,
    SalesReportRowResponse,
    page_meta,
    summary_response,
)
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.enums import InventoryStatus, NotificationStatus
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.report_filters import ExportFormat, ReportFilters, ReportType
from webstudio_backend.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

ReportsReadDep = Annotated[AuthenticatedUser, Depends(require_permission("reports:read"))]

_EXPORT_REPORT_TYPES = frozenset(
    {
        ReportType.INVENTORY,
        ReportType.SALES,
        ReportType.LOCATION,
        ReportType.BRAND,
        ReportType.PRODUCT_MODEL,
        ReportType.AUDIT,
        ReportType.NOTIFICATION,
    },
)


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return Envelope(
        data=data,
        meta=meta,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _page_meta(page: int, page_size: int, total_items: int, total_pages: int) -> ResponseMeta:
    return ResponseMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
    )


def _filters(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    status: InventoryStatus | None = None,
    notification_status: NotificationStatus | None = None,
) -> ReportFilters:
    return ReportFilters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
        inventory_status=status,
        notification_status=notification_status,
    )


@router.get("/inventory")
async def inventory_report(
    request: Request,
    current: ReportsReadDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    status: InventoryStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _filters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        status=status,
    )
    rows, summary = await ReportService(db_session).inventory_report(
        filters,
        PageParams(page=page, page_size=page_size),
    )
    response = InventoryReportResponse(
        generated_at=datetime.now(UTC),
        filters=ReportFiltersApplied.from_filters(filters),
        summary=summary_response(summary),
        rows=[InventoryReportRowResponse.from_row(row) for row in rows.items],
    )
    meta = page_meta(rows)
    return _envelope(request, response.model_dump(), _page_meta(**meta))


@router.get("/sales")
async def sales_report(
    request: Request,
    current: ReportsReadDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _filters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
    )
    rows = await ReportService(db_session).sales_report(filters, PageParams(page=page, page_size=page_size))
    response = SalesReportResponse(
        generated_at=datetime.now(UTC),
        filters=ReportFiltersApplied.from_filters(filters),
        rows=[SalesReportRowResponse.from_row(row) for row in rows.items],
    )
    meta = page_meta(rows)
    return _envelope(request, response.model_dump(), _page_meta(**meta))


@router.get("/audit")
async def audit_report(
    request: Request,
    current: ReportsReadDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _filters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
    )
    rows = await ReportService(db_session).audit_report(filters, PageParams(page=page, page_size=page_size))
    response = AuditReportResponse(
        generated_at=datetime.now(UTC),
        filters=ReportFiltersApplied.from_filters(filters),
        rows=[AuditReportRowResponse.from_row(row) for row in rows.items],
    )
    meta = page_meta(rows)
    return _envelope(request, response.model_dump(), _page_meta(**meta))


@router.get("/notifications")
async def notifications_report(
    request: Request,
    current: ReportsReadDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id: int | None = None,
    notification_status: NotificationStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _filters(
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        notification_status=notification_status,
    )
    rows = await ReportService(db_session).notifications_report(
        filters,
        PageParams(page=page, page_size=page_size),
    )
    response = NotificationReportResponse(
        generated_at=datetime.now(UTC),
        filters=ReportFiltersApplied.from_filters(filters),
        rows=[NotificationReportRowResponse.from_row(row) for row in rows.items],
    )
    meta = page_meta(rows)
    return _envelope(request, response.model_dump(), _page_meta(**meta))


@router.get("/export")
async def export_report(
    current: ReportsReadDep,
    db_session: AsyncSession = DbSessionDep,
    report_type: ReportType = Query(...),
    format: ExportFormat = Query(default=ExportFormat.XLSX, alias="format"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    status: InventoryStatus | None = None,
    notification_status: NotificationStatus | None = None,
) -> Response:
    del current
    if report_type not in _EXPORT_REPORT_TYPES:
        raise AppError(
            code="VALIDATION_ERROR",
            message=f"Unsupported report type: {report_type.value}",
            status_code=422,
        )

    filters = _filters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
        status=status,
        notification_status=notification_status,
    )
    content, media_type, filename = await ReportService(db_session).export_report(
        report_type=report_type,
        export_format=format,
        filters=filters,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
