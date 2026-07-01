"""Sales workspace API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import SalesViewDep
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.sales import SaleDetailResponse, SaleListItem
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.enums import SaleSource
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.report_filters import ReportFilters
from webstudio_backend.services.report_service import ReportService

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
    del current
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
    result = await ReportService(db_session).sales_report(filters, PageParams(page=page, page_size=page_size))
    return _envelope(
        request,
        [SaleListItem.from_row(row).model_dump() for row in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/{sale_id}")
async def get_sale(
    request: Request,
    sale_id: int,
    current: SalesViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    row = await ReportService(db_session).get_sale_detail(sale_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return _envelope(request, SaleDetailResponse.from_row(row).model_dump())
