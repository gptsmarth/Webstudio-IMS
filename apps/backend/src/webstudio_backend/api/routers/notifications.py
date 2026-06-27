"""Notification Center API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.notification_errors import raise_notification_error
from webstudio_backend.api.schemas.notification import NotificationDetail
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.database.enums import (
    NotificationCategory,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.exceptions import (
    NotificationAlreadyResolvedError,
    NotificationNotFoundError,
)
from webstudio_backend.infrastructure.repositories.notification_filters import NotificationSearchFilters
from webstudio_backend.services.notification_service import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])

NotificationReadDep = Annotated[AuthenticatedUser, Depends(require_permission("notifications:read"))]
NotificationResolveDep = Annotated[AuthenticatedUser, Depends(require_permission("notifications:resolve"))]


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
async def list_notifications(
    request: Request,
    current: NotificationReadDep,
    db_session: AsyncSession = DbSessionDep,
    notification_type: NotificationType | None = None,
    category: NotificationCategory | None = None,
    severity: NotificationSeverity | None = None,
    status: NotificationStatus | None = None,
    is_read: bool | None = None,
    is_resolved: bool | None = None,
    tally_company_name: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    del current
    filters = NotificationSearchFilters(
        notification_type=notification_type,
        category=category,
        severity=severity,
        status=status,
        is_read=is_read,
        is_resolved=is_resolved,
        tally_company_name=tally_company_name,
    )
    result = await NotificationService(db_session).list_notifications(
        filters,
        PageParams(page=page, page_size=page_size),
    )
    return _envelope(
        request,
        [NotificationDetail.from_model(entry).model_dump() for entry in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/{notification_id}")
async def get_notification(
    request: Request,
    notification_id: int,
    current: NotificationReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    notification = await NotificationService(db_session).get_notification(notification_id)
    if notification is None:
        raise AppError(code="NOT_FOUND", message="Notification not found", status_code=404)
    return _envelope(request, NotificationDetail.from_model(notification).model_dump())


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    request: Request,
    notification_id: int,
    current: NotificationReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    service = NotificationService(db_session)
    try:
        notification = await service.mark_read(notification_id)
    except NotificationNotFoundError as exc:
        raise_notification_error(exc)
    return _envelope(request, NotificationDetail.from_model(notification).model_dump())


@router.patch("/{notification_id}/resolve")
async def resolve_notification(
    request: Request,
    notification_id: int,
    current: NotificationResolveDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = NotificationService(db_session)
    try:
        notification = await service.mark_resolved(
            notification_id,
            resolved_by_user_id=current.user.id,
        )
    except (NotificationNotFoundError, NotificationAlreadyResolvedError) as exc:
        raise_notification_error(exc)
    return _envelope(request, NotificationDetail.from_model(notification).model_dump())
