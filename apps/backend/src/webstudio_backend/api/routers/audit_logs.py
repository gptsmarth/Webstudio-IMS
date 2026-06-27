"""Audit log API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.audit_log import AuditLogEntry
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.exceptions import InventoryItemNotFoundError

router = APIRouter(prefix="/api/v1/audit_logs", tags=["audit"])


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


@router.get("")
async def search_audit_logs(
    request: Request,
    db_session: AsyncSession = DbSessionDep,
    entity_type: str | None = None,
    entity_id: str | None = None,
    inventory_item_id: uuid.UUID | None = None,
    serial_number: str | None = None,
    product_model_id: uuid.UUID | None = None,
    brand_id: int | None = None,
    actor_user_id: int | None = None,
    action: AuditAction | None = None,
    source: AuditSource | None = None,
    created_at_from: datetime | None = None,
    created_at_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    repository = AuditLogRepository(db_session)
    filters = AuditLogSearchFilters(
        entity_type=entity_type,
        entity_id=entity_id,
        inventory_item_id=inventory_item_id,
        serial_number=serial_number,
        product_model_id=product_model_id,
        brand_id=brand_id,
        actor_user_id=actor_user_id,
        action=action,
        source=source,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
    )
    result = await repository.search(filters, PageParams(page=page, page_size=page_size))
    return _envelope(
        request,
        [AuditLogEntry.from_model(entry).model_dump() for entry in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/lifecycle/by-serial/{serial_number}")
async def audit_lifecycle_by_serial(
    request: Request,
    serial_number: str,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    repository = AuditLogRepository(db_session)
    try:
        result = await repository.get_by_serial_number(
            serial_number,
            PageParams(page=page, page_size=page_size),
        )
    except InventoryItemNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(
        request,
        [AuditLogEntry.from_model(entry).model_dump() for entry in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/by-entity/{entity_type}/{entity_id}")
async def audit_history_by_entity(
    request: Request,
    entity_type: str,
    entity_id: str,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    repository = AuditLogRepository(db_session)
    result = await repository.get_by_entity(
        entity_type,
        entity_id,
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [AuditLogEntry.from_model(entry).model_dump() for entry in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/by-inventory-item/{inventory_item_id}")
async def audit_history_by_inventory_item(
    request: Request,
    inventory_item_id: uuid.UUID,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    repository = AuditLogRepository(db_session)
    result = await repository.get_by_inventory_item(
        inventory_item_id,
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [AuditLogEntry.from_model(entry).model_dump() for entry in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/{audit_log_id}")
async def get_audit_log(
    request: Request,
    audit_log_id: uuid.UUID,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    entry = await AuditLogRepository(db_session).get_by_id(audit_log_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return _envelope(request, AuditLogEntry.from_model(entry).model_dump())
