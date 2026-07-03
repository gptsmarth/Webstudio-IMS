"""Reports and export API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import ReportsExportDep, ReportsViewDep
from webstudio_backend.api.response_helpers import build_page_meta
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
from webstudio_backend.infrastructure.database.enums import (
    AuditAction,
    AuditSource,
    InventoryStatus,
    LocationType,
    NotificationCategory,
    NotificationStatus,
    NotificationType,
    SaleSource,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.report_filters import (
    ExportFormat,
    ReportFilters,
    ReportType,
)
from webstudio_backend.services.report_service import ReportService

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])

_EXPORT_REPORT_TYPES = frozenset(
    {
        ReportType.INVENTORY,
        ReportType.SALES,
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
    return build_page_meta(page, page_size, total_items, total_pages)


def _common_report_params(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    purchase_date_from: date | None = None,
    purchase_date_to: date | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    location_type: LocationType | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    status: InventoryStatus | None = None,
    is_archived: bool | None = None,
    serial_number: str | None = None,
    color: str | None = None,
    notification_status: NotificationStatus | None = None,
    notification_type: NotificationType | None = None,
    notification_category: NotificationCategory | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    payment_mode: str | None = None,
    sale_source: SaleSource | None = None,
    audit_action: AuditAction | None = None,
    audit_source: AuditSource | None = None,
    actor_role: str | None = None,
    security_only: bool = False,
    audit_severity: str | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
) -> ReportFilters:
    return ReportFilters(
        date_from=date_from,
        date_to=date_to,
        purchase_date_from=purchase_date_from,
        purchase_date_to=purchase_date_to,
        brand_id=brand_id,
        location_id=location_id,
        location_type=location_type,
        product_model_id=product_model_id,
        user_id=user_id,
        inventory_status=status,
        is_archived=is_archived,
        serial_number=serial_number,
        color=color,
        notification_status=notification_status,
        notification_type=notification_type,
        notification_category=notification_category,
        invoice_number=invoice_number,
        customer_name=customer_name,
        payment_mode=payment_mode,
        sale_source=sale_source,
        audit_action=audit_action,
        audit_source=audit_source,
        actor_role=actor_role,
        security_only=security_only,
        audit_severity=audit_severity,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
    )


@router.get("/inventory")
async def inventory_report(
    request: Request,
    current: ReportsViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    purchase_date_from: date | None = None,
    purchase_date_to: date | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    location_type: LocationType | None = None,
    product_model_id: uuid.UUID | None = None,
    status: InventoryStatus | None = None,
    is_archived: bool | None = None,
    serial_number: str | None = None,
    color: str | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _common_report_params(
        date_from=date_from,
        date_to=date_to,
        purchase_date_from=purchase_date_from,
        purchase_date_to=purchase_date_to,
        brand_id=brand_id,
        location_id=location_id,
        location_type=location_type,
        product_model_id=product_model_id,
        status=status,
        is_archived=is_archived,
        serial_number=serial_number,
        color=color,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
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
    current: ReportsViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    location_type: LocationType | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    payment_mode: str | None = None,
    sale_source: SaleSource | None = None,
    serial_number: str | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _common_report_params(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        location_type=location_type,
        product_model_id=product_model_id,
        user_id=user_id,
        invoice_number=invoice_number,
        customer_name=customer_name,
        payment_mode=payment_mode,
        sale_source=sale_source,
        serial_number=serial_number,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
    )
    rows = await ReportService(db_session).sales_report(
        filters, PageParams(page=page, page_size=page_size)
    )
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
    current: ReportsViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    audit_action: AuditAction | None = None,
    audit_source: AuditSource | None = None,
    actor_role: str | None = None,
    serial_number: str | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _common_report_params(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
        audit_action=audit_action,
        audit_source=audit_source,
        actor_role=actor_role,
        serial_number=serial_number,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
    )
    rows = await ReportService(db_session).audit_report(
        filters, PageParams(page=page, page_size=page_size)
    )
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
    current: ReportsViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id: int | None = None,
    notification_status: NotificationStatus | None = Query(default=None, alias="status"),
    notification_type: NotificationType | None = None,
    notification_category: NotificationCategory | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = _common_report_params(
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        notification_status=notification_status,
        notification_type=notification_type,
        notification_category=notification_category,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
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
    current: ReportsExportDep,
    db_session: AsyncSession = DbSessionDep,
    report_type: ReportType = Query(...),
    format: ExportFormat = Query(default=ExportFormat.XLSX, alias="format"),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    purchase_date_from: date | None = None,
    purchase_date_to: date | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    location_type: LocationType | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    status: InventoryStatus | None = None,
    is_archived: bool | None = None,
    serial_number: str | None = None,
    color: str | None = None,
    notification_status: NotificationStatus | None = None,
    notification_type: NotificationType | None = None,
    notification_category: NotificationCategory | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    payment_mode: str | None = None,
    sale_source: SaleSource | None = None,
    audit_action: AuditAction | None = None,
    audit_source: AuditSource | None = None,
    actor_role: str | None = None,
    security_only: bool = False,
    audit_severity: str | None = None,
    search: str | None = None,
    sort_field: str | None = None,
    sort_direction: str | None = None,
) -> Response:
    del current
    if report_type not in _EXPORT_REPORT_TYPES:
        raise AppError(
            code="VALIDATION_ERROR",
            message=f"Unsupported report type: {report_type.value}",
            status_code=422,
        )

    filters = _common_report_params(
        date_from=date_from,
        date_to=date_to,
        purchase_date_from=purchase_date_from,
        purchase_date_to=purchase_date_to,
        brand_id=brand_id,
        location_id=location_id,
        location_type=location_type,
        product_model_id=product_model_id,
        user_id=user_id,
        status=status,
        is_archived=is_archived,
        serial_number=serial_number,
        color=color,
        notification_status=notification_status,
        notification_type=notification_type,
        notification_category=notification_category,
        invoice_number=invoice_number,
        customer_name=customer_name,
        payment_mode=payment_mode,
        sale_source=sale_source,
        audit_action=audit_action,
        audit_source=audit_source,
        actor_role=actor_role,
        security_only=security_only,
        audit_severity=audit_severity,
        search=search,
        sort_field=sort_field,
        sort_direction=sort_direction,
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
