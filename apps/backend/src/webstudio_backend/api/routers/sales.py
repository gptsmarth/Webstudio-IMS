"""Sales workspace API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, SalesCancelDep, SalesViewDep
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.sales_errors import raise_sale_error
from webstudio_backend.api.schemas.inventory import InventoryItemDetail
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.sales import (
    CancelledSaleSummary,
    CancelSaleRequest,
    CancelSaleResponse,
    SaleDetailResponse,
    SaleListItem,
)
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import SaleSource, UserRole
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.report_filters import ReportFilters
from webstudio_backend.services.report_service import ReportService
from webstudio_backend.services.sale_service import SaleService

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


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


def _can_view_purchase_price(current: AuthenticatedUser) -> bool:
    return current.user.role in {UserRole.MAIN_ADMIN, UserRole.ADMIN}


def _actor(current: AuthenticatedUser) -> AuditActor:
    return AuditActor(
        user_id=current.user.id,
        display_name=current.user.display_name,
        role=current.user.role.value,
    )


def _sale_list_payload(row, *, current: AuthenticatedUser) -> dict:
    include_purchase = _can_view_purchase_price(current)
    response = SaleListItem.from_row(row, include_purchase_price=include_purchase)
    exclude = set() if include_purchase else {"purchase_price"}
    return response.model_dump(exclude=exclude)


def _sale_detail_payload(row, *, current: AuthenticatedUser) -> dict:
    include_purchase = _can_view_purchase_price(current)
    response = SaleDetailResponse.from_row(row, include_purchase_price=include_purchase)
    exclude = set() if include_purchase else {"purchase_price"}
    return response.model_dump(exclude=exclude)


def _parse_legacy_sort(sort: str | None) -> tuple[str | None, str | None]:
    if not sort:
        return None, None
    if ":" in sort:
        field, direction = sort.split(":", 1)
        return field.strip() or None, direction.strip() or None
    return sort.strip() or None, None


@router.get("")
async def list_sales(
    request: Request,
    current: SalesViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    payment_mode: str | None = None,
    sale_source: SaleSource | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort: str | None = Query(default="sold_at:desc"),
    sort_field: str | None = None,
    sort_direction: str | None = None,
) -> dict:
    legacy_field, legacy_direction = _parse_legacy_sort(sort)
    filters = ReportFilters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
        invoice_number=invoice_number,
        customer_name=customer_name,
        payment_mode=payment_mode,
        sale_source=sale_source,
        search=search,
        sort_field=sort_field or legacy_field,
        sort_direction=sort_direction or legacy_direction,
    )
    result = await ReportService(db_session).sales_report(
        filters, PageParams(page=page, page_size=page_size)
    )
    return _envelope(
        request,
        [_sale_list_payload(row, current=current) for row in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/{sale_id}")
async def get_sale(
    request: Request,
    sale_id: int,
    current: SalesViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    row = await ReportService(db_session).get_sale_detail(sale_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return _envelope(request, _sale_detail_payload(row, current=current))


@router.post("/{sale_id}/cancel")
async def cancel_sale(
    request: Request,
    sale_id: int,
    body: CancelSaleRequest,
    current: SalesCancelDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        result = await SaleService(db_session).cancel_sale(
            sale_id,
            reason=body.reason,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_sale_error(exc)

    include_purchase = _can_view_purchase_price(current)
    response = CancelSaleResponse(
        inventory=InventoryItemDetail.from_row(
            result.inventory,
            include_purchase_price=include_purchase,
        ),
        sale=CancelledSaleSummary(
            id=result.sale.id,
            invoice_number=result.sale.invoice_number,
            serial_number=result.restored_serial_number,
            cancelled_at=result.sale.cancelled_at,
            cancellation_reason=result.sale.cancellation_reason,
        ),
    )
    payload = response.model_dump()
    if not include_purchase:
        payload["inventory"].pop("purchase_price", None)
    return _envelope(request, payload)
