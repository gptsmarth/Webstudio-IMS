"""Inventory API endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.inventory_errors import raise_inventory_error
from webstudio_backend.api.schemas.inventory import (
    CreateInventoryItemRequest,
    InventoryItemDetail,
    MarkSoldRequest,
    MarkSoldResponse,
    SaleDetail,
    TransferLocationRequest,
    UpdateInventoryItemRequest,
    UpdateSellingPriceRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import InventoryStatus, UserRole
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam
from webstudio_backend.infrastructure.repositories.inventory_item_filters import InventorySearchFilters
from webstudio_backend.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

InventoryReadDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:read"))]
InventoryWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:write"))]
SellingPriceWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:selling_price:write"))]
LocationTransferDep = Annotated[AuthenticatedUser, Depends(require_permission("location:transfer"))]
SalesReflectDep = Annotated[AuthenticatedUser, Depends(require_permission("sales:reflect"))]

_ALLOWED_SORT_FIELDS = frozenset(
    {
        "serial_number",
        "status",
        "color",
        "created_at",
        "updated_at",
        "purchase_date",
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
        total_records=total_items,
        current_page=page,
    )


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


def _can_view_purchase_price(current: AuthenticatedUser) -> bool:
    return current.user.role in {UserRole.MAIN_ADMIN, UserRole.ADMIN}


def _item_payload(row, current: AuthenticatedUser) -> dict:
    include_purchase = _can_view_purchase_price(current)
    detail = InventoryItemDetail.from_row(row, include_purchase_price=include_purchase)
    exclude = set() if include_purchase else {"purchase_price"}
    return detail.model_dump(exclude=exclude)


def _parse_sort(sort: str | None) -> list[SortParam]:
    if not sort:
        return [SortParam("updated_at", "desc")]
    if ":" in sort:
        field, direction = sort.split(":", 1)
    else:
        field, direction = sort, "asc"
    direction = direction.lower()
    if direction not in {"asc", "desc"}:
        raise AppError(
            "VALIDATION_ERROR",
            f"Invalid sort direction: {direction}",
            status_code=422,
        )
    if field not in _ALLOWED_SORT_FIELDS:
        raise AppError(
            "VALIDATION_ERROR",
            f"Unsupported sort field: {field}",
            status_code=422,
        )
    return [SortParam(field, direction)]


@router.get("")
async def list_inventory(
    request: Request,
    current: InventoryReadDep,
    db_session: AsyncSession = DbSessionDep,
    brand_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    current_location_id: int | None = None,
    status_filter: InventoryStatus | None = Query(default=None, alias="status"),
    is_archived: bool | None = None,
    include_archived: bool = False,
    serial_number: str | None = None,
    brand: str | None = Query(default=None, description="Brand name search"),
    product_model: str | None = Query(default=None, description="Product model search"),
    location: str | None = Query(default=None, description="Location name search"),
    search: str | None = None,
    purchase_date_from: date | None = None,
    purchase_date_to: date | None = None,
    created_at_from: date | None = None,
    created_at_to: date | None = None,
    color: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort: str | None = Query(default="updated_at:desc"),
) -> dict:
    sort_params = _parse_sort(sort)

    filters = InventorySearchFilters(
        brand_id=brand_id,
        product_model_id=product_model_id,
        current_location_id=current_location_id,
        status=status_filter,
        is_archived=is_archived,
        include_archived=include_archived,
        serial_number=serial_number,
        brand_name=brand,
        product_model=product_model,
        location_name=location,
        search=search,
        purchase_date_from=purchase_date_from,
        purchase_date_to=purchase_date_to,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        color=color,
    )
    result = await InventoryService(db_session).list_items(
        filters,
        PageParams(page=page, page_size=page_size),
        sort_params,
    )
    return _envelope(
        request,
        [_item_payload(row, current) for row in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_inventory(
    request: Request,
    body: CreateInventoryItemRequest,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        detail = await InventoryService(db_session).create_item(
            serial_number=body.serial_number,
            product_model_id=body.product_model_id,
            color=body.color,
            current_location_id=body.current_location_id,
            status=body.status,
            purchase_date=body.purchase_date,
            purchase_price=body.purchase_price,
            selling_price=body.selling_price,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.get("/by-serial/{serial_number}")
async def get_inventory_by_serial(
    request: Request,
    serial_number: str,
    current: InventoryReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    detail = await InventoryService(db_session).get_by_serial(serial_number)
    if detail is None:
        raise AppError(
            "SERIAL_NOT_FOUND",
            "Inventory item not found for serial number.",
            status_code=404,
        )
    return _envelope(request, _item_payload(detail, current))


@router.get("/{inventory_id}")
async def get_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    detail = await InventoryService(db_session).get_item(inventory_id)
    if detail is None:
        raise AppError(
            "NOT_FOUND",
            "Inventory item not found.",
            status_code=404,
        )
    return _envelope(request, _item_payload(detail, current))


@router.patch("/{inventory_id}")
async def update_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    body: UpdateInventoryItemRequest,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    if not body.model_fields_set:
        raise AppError(
            "VALIDATION_ERROR",
            "At least one field must be provided for update.",
            status_code=422,
        )
    fields_set = body.model_fields_set
    try:
        detail = await InventoryService(db_session).update_item(
            inventory_id,
            actor=_actor(current),
            serial_number=body.serial_number,
            product_model_id=body.product_model_id,
            color=body.color,
            status=body.status,
            purchase_date=body.purchase_date,
            set_purchase_date="purchase_date" in fields_set,
            purchase_price=body.purchase_price,
            set_purchase_price="purchase_price" in fields_set,
            selling_price=body.selling_price,
            set_selling_price="selling_price" in fields_set,
        )
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.patch("/{inventory_id}/selling-price")
async def update_inventory_selling_price(
    request: Request,
    inventory_id: uuid.UUID,
    body: UpdateSellingPriceRequest,
    current: SellingPriceWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        detail = await InventoryService(db_session).update_selling_price(
            inventory_id,
            selling_price=body.selling_price,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.post("/{inventory_id}/archive")
async def archive_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        detail = await InventoryService(db_session).archive_item(inventory_id, actor=_actor(current))
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.post("/{inventory_id}/restore")
async def restore_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        detail = await InventoryService(db_session).restore_item(inventory_id, actor=_actor(current))
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.patch("/{inventory_id}/location")
async def transfer_inventory_location(
    request: Request,
    inventory_id: uuid.UUID,
    body: TransferLocationRequest,
    current: LocationTransferDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        detail = await InventoryService(db_session).transfer_location(
            inventory_id,
            to_location_id=body.location_id,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_inventory_error(exc)
    return _envelope(request, _item_payload(detail, current))


@router.patch("/{inventory_id}/mark-sold")
async def mark_inventory_sold(
    request: Request,
    inventory_id: uuid.UUID,
    body: MarkSoldRequest,
    current: SalesReflectDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        result = await InventoryService(db_session).mark_as_sold(
            inventory_id,
            invoice_number=body.invoice_number,
            customer_name=body.customer_name,
            payment_mode=body.payment_mode,
            sale_date=body.sale_date,
            remarks=body.remarks,
            sale_amount=float(body.sale_amount) if body.sale_amount is not None else None,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_inventory_error(exc)

    response = MarkSoldResponse(
        inventory=InventoryItemDetail.from_row(
            result.inventory,
            include_purchase_price=_can_view_purchase_price(current),
        ),
        sale=SaleDetail.from_model(
            result.sale,
            serial_number=result.inventory.item.serial_number,
        ),
    )
    return _envelope(request, response.model_dump())
