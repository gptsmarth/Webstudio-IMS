"""Integration API key administration (Main Admin only)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, MainAdminDep
from webstudio_backend.api.schemas.integration_key import (
    CreateIntegrationKeyRequest,
    IntegrationKeySummary,
    UpdateIntegrationKeyRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.services.integration_key_service import (
    IntegrationKeyNotFoundError,
    IntegrationKeyService,
)

router = APIRouter(prefix="/api/v1/admin/integration-keys", tags=["admin"])


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


@router.get("")
async def list_integration_keys(
    request: Request,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
    include_archived: bool = Query(default=False),
) -> dict:
    keys = await IntegrationKeyService(db_session).list_keys(include_archived=include_archived)
    payload = [IntegrationKeySummary.model_validate(item).model_dump() for item in keys]
    return _envelope(request, payload)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_integration_key(
    request: Request,
    body: CreateIntegrationKeyRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        record = await IntegrationKeyService(db_session).create_key(
            service_type=body.service_type,
            label=body.label,
            api_key=body.api_key,
            actor=_actor(current),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return _envelope(request, IntegrationKeySummary.model_validate(record).model_dump())


@router.patch("/{key_id}")
async def update_integration_key(
    request: Request,
    key_id: int,
    body: UpdateIntegrationKeyRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    if body.label is None and body.api_key is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update",
        )
    try:
        record = await IntegrationKeyService(db_session).update_key(
            key_id,
            label=body.label,
            api_key=body.api_key,
            actor=_actor(current),
        )
    except IntegrationKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return _envelope(request, IntegrationKeySummary.model_validate(record).model_dump())


@router.post("/{key_id}/archive")
async def archive_integration_key(
    request: Request,
    key_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        record = await IntegrationKeyService(db_session).archive_key(key_id, actor=_actor(current))
    except IntegrationKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, IntegrationKeySummary.model_validate(record).model_dump())


@router.post("/{key_id}/restore")
async def restore_integration_key(
    request: Request,
    key_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        record = await IntegrationKeyService(db_session).restore_key(key_id, actor=_actor(current))
    except IntegrationKeyNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, IntegrationKeySummary.model_validate(record).model_dump())
