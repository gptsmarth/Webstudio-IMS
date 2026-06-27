"""Inventory API endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.schemas.inventory import (
    CreateInventoryItemRequest,
    InventoryItemDetail,
    UpdateInventoryItemRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import InventoryStatus
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.database.repositories.sorting import SortParam
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemArchiveNotAllowedError,
    InventoryItemNotFoundError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_filters import InventorySearchFilters
from webstudio_backend.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

InventoryReadDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:read"))]
InventoryWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:write"))]


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


def _parse_sort(sort: str | None) -> list[SortParam]:
    if not sort:
        return [SortParam("updated_at", "desc")]
    if ":" in sort:
        field, direction = sort.split(":", 1)
    else:
        field, direction = sort, "asc"
    direction = direction.lower()
    if direction not in {"asc", "desc"}:
        raise ValueError(f"Invalid sort direction: {direction}")
    allowed = {
        "serial_number",
        "status",
        "color",
        "created_at",
        "updated_at",
        "purchase_date",
        "warranty_expiry",
    }
    if field not in allowed:
        raise ValueError(f"Unsupported sort field: {field}")
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
    warranty_expiry_from: date | None = None,
    warranty_expiry_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort: str | None = Query(default="updated_at:desc"),
) -> dict:
    del current
    try:
        sort_params = _parse_sort(sort)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

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
        warranty_expiry_from=warranty_expiry_from,
        warranty_expiry_to=warranty_expiry_to,
    )
    result = await InventoryService(db_session).list_items(
        filters,
        PageParams(page=page, page_size=page_size),
        sort_params,
    )
    return _envelope(
        request,
        [InventoryItemDetail.from_row(row).model_dump() for row in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_inventory(
    request: Request,
    body: CreateInventoryItemRequest,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = InventoryService(db_session)
    try:
        detail = await service.create_item(
            serial_number=body.serial_number,
            product_model_id=body.product_model_id,
            color=body.color,
            current_location_id=body.current_location_id,
            status=body.status,
            purchase_date=body.purchase_date,
            warranty_expiry=body.warranty_expiry,
            actor=_actor(current),
        )
    except DuplicateSerialNumberError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InactiveProductModelError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InactiveLocationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())


@router.get("/by-serial/{serial_number}")
async def get_inventory_by_serial(
    request: Request,
    serial_number: str,
    current: InventoryReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    detail = await InventoryService(db_session).get_by_serial(serial_number)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())


@router.get("/{inventory_id}")
async def get_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    detail = await InventoryService(db_session).get_item(inventory_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())


@router.patch("/{inventory_id}")
async def update_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    body: UpdateInventoryItemRequest,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    fields_set = body.model_fields_set
    service = InventoryService(db_session)
    try:
        detail = await service.update_item(
            inventory_id,
            actor=_actor(current),
            serial_number=body.serial_number,
            product_model_id=body.product_model_id,
            color=body.color,
            current_location_id=body.current_location_id,
            status=body.status,
            purchase_date=body.purchase_date,
            warranty_expiry=body.warranty_expiry,
            set_purchase_date="purchase_date" in fields_set,
            set_warranty_expiry="warranty_expiry" in fields_set,
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateSerialNumberError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InactiveProductModelError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except InactiveLocationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())


@router.post("/{inventory_id}/archive")
async def archive_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = InventoryService(db_session)
    try:
        detail = await service.archive_item(inventory_id, actor=_actor(current))
    except InventoryItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InventoryItemArchiveNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())


@router.post("/{inventory_id}/restore")
async def restore_inventory(
    request: Request,
    inventory_id: uuid.UUID,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = InventoryService(db_session)
    try:
        detail = await service.restore_item(inventory_id, actor=_actor(current))
    except InventoryItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, InventoryItemDetail.from_row(detail).model_dump())
