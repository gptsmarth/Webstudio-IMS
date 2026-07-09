"""Audit log API endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuditLifecycleDep, AuditViewDep, AuditViewOrLifecycleDep
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.schemas.audit_log import AuditLogDetail, AuditLogListEntry
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.enums import AuditAction, AuditSource
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository

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
    return build_page_meta(page, page_size, total_items, total_pages)


def _parse_date_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def _parse_date_end(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=UTC)


def _build_filters(
    *,
    entity_type: str | None,
    entity_id: str | None,
    inventory_item_id: uuid.UUID | None,
    serial_number: str | None,
    product_model_id: uuid.UUID | None,
    brand_id: int | None,
    actor_user_id: int | None,
    actor_role: str | None,
    action: AuditAction | None,
    source: AuditSource | None,
    location_id: int | None,
    invoice_number: str | None,
    model_number: str | None,
    search: str | None,
    result: str | None,
    severity: str | None,
    security_only: bool,
    created_at_from: datetime | date | None,
    created_at_to: datetime | date | None,
) -> AuditLogSearchFilters:
    parsed_from = (
        _parse_date_start(created_at_from) if type(created_at_from) is date else created_at_from
    )
    parsed_to = _parse_date_end(created_at_to) if type(created_at_to) is date else created_at_to
    return AuditLogSearchFilters(
        entity_type=entity_type,
        entity_id=entity_id,
        inventory_item_id=inventory_item_id,
        serial_number=serial_number,
        product_model_id=product_model_id,
        brand_id=brand_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        source=source,
        location_id=location_id,
        invoice_number=invoice_number,
        model_number=model_number,
        search=search,
        result=result,
        severity=severity,
        security_only=security_only,
        created_at_from=parsed_from,
        created_at_to=parsed_to,
    )


@router.get("")
async def search_audit_logs(
    request: Request,
    current: AuditViewDep,
    db_session: AsyncSession = DbSessionDep,
    entity_type: str | None = None,
    entity_id: str | None = None,
    inventory_item_id: uuid.UUID | None = None,
    serial_number: str | None = None,
    product_model_id: uuid.UUID | None = None,
    brand_id: int | None = None,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    action: AuditAction | None = None,
    source: AuditSource | None = None,
    location_id: int | None = None,
    invoice_number: str | None = None,
    model_number: str | None = None,
    search: str | None = None,
    result: str | None = Query(default=None, pattern="^(success|failure)$"),
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    security_only: bool = Query(default=False),
    created_at_from: datetime | date | None = None,
    created_at_to: datetime | date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    _ = current
    repository = AuditLogRepository(db_session)
    filters = _build_filters(
        entity_type=entity_type,
        entity_id=entity_id,
        inventory_item_id=inventory_item_id,
        serial_number=serial_number,
        product_model_id=product_model_id,
        brand_id=brand_id,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        source=source,
        location_id=location_id,
        invoice_number=invoice_number,
        model_number=model_number,
        search=search,
        result=result,
        severity=severity,
        security_only=security_only,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
    )
    page_result = await repository.search_enriched(
        filters, PageParams(page=page, page_size=page_size)
    )
    return _envelope(
        request,
        [AuditLogListEntry.from_enriched(row).model_dump() for row in page_result.items],
        _page_meta(
            page_result.page,
            page_result.page_size,
            page_result.total_items,
            page_result.total_pages,
        ),
    )


@router.get("/lifecycle/by-serial/{serial_number}")
async def audit_lifecycle_by_serial(
    request: Request,
    current: AuditLifecycleDep,
    serial_number: str,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    _ = current
    repository = AuditLogRepository(db_session)
    item_exists = await db_session.scalar(
        select(InventoryItem.id).where(
            func.lower(InventoryItem.serial_number) == serial_number.strip().lower(),
        ),
    )
    if item_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    enriched = await repository.search_enriched(
        AuditLogSearchFilters(serial_number=serial_number),
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [AuditLogListEntry.from_enriched(row).model_dump() for row in enriched.items],
        _page_meta(enriched.page, enriched.page_size, enriched.total_items, enriched.total_pages),
    )


@router.get("/by-entity/{entity_type}/{entity_id}")
async def audit_history_by_entity(
    request: Request,
    current: AuditViewDep,
    entity_type: str,
    entity_id: str,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    _ = current
    repository = AuditLogRepository(db_session)
    enriched = await repository.search_enriched(
        AuditLogSearchFilters(entity_type=entity_type, entity_id=entity_id),
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [AuditLogListEntry.from_enriched(row).model_dump() for row in enriched.items],
        _page_meta(enriched.page, enriched.page_size, enriched.total_items, enriched.total_pages),
    )


@router.get("/by-inventory-item/{inventory_item_id}")
async def audit_history_by_inventory_item(
    request: Request,
    current: AuditViewOrLifecycleDep,
    inventory_item_id: uuid.UUID,
    db_session: AsyncSession = DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    _ = current
    repository = AuditLogRepository(db_session)
    enriched = await repository.search_enriched(
        AuditLogSearchFilters(inventory_item_id=inventory_item_id),
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [AuditLogListEntry.from_enriched(row).model_dump() for row in enriched.items],
        _page_meta(enriched.page, enriched.page_size, enriched.total_items, enriched.total_pages),
    )


@router.get("/{audit_log_id}")
async def get_audit_log(
    request: Request,
    current: AuditViewDep,
    audit_log_id: uuid.UUID,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    _ = current
    row = await AuditLogRepository(db_session).get_enriched_by_id(audit_log_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log not found")
    return _envelope(request, AuditLogDetail.from_enriched(row).model_dump())
