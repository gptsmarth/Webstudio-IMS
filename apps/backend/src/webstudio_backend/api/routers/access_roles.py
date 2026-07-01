"""Custom access role administration endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import MainAdminDep
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.schemas.access_role import (
    CreateCustomAccessRoleRequest,
    CustomAccessRoleDetail,
    CustomAccessRoleSummary,
    PermissionCatalogResponse,
    UpdateCustomAccessRoleRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.permissions import ASSIGNABLE_PERMISSIONS
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.services.custom_access_role_service import (
    CustomAccessRoleInUseError,
    CustomAccessRoleNotFoundError,
    CustomAccessRoleService,
    DuplicateAccessRoleNameError,
)

router = APIRouter(prefix="/api/v1/access-roles", tags=["access-roles"])


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return Envelope(
        data=data,
        meta=meta,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _actor(current: MainAdminDep) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


@router.get("/catalog")
async def permission_catalog(request: Request, current: MainAdminDep) -> dict:
    del current
    payload = PermissionCatalogResponse(permissions=list(ASSIGNABLE_PERMISSIONS))
    return _envelope(request, payload.model_dump())


@router.get("")
async def list_access_roles(
    request: Request,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
    include_inactive: bool = Query(default=False),
) -> dict:
    del current
    service = CustomAccessRoleService(db_session)
    roles = await service.list_roles(include_inactive=include_inactive)
    items = []
    for role in roles:
        assigned = await service.assigned_user_count(role.id)
        items.append(CustomAccessRoleSummary.from_model(role, assigned_user_count=assigned).model_dump())
    return _envelope(request, items)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_access_role(
    request: Request,
    body: CreateCustomAccessRoleRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = CustomAccessRoleService(db_session)
    try:
        role = await service.create_role(
            name=body.name,
            description=body.description,
            permissions=body.permissions,
            actor=_actor(current),
        )
    except DuplicateAccessRoleNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    assigned = await service.assigned_user_count(role.id)
    return _envelope(request, CustomAccessRoleDetail.from_model(role, assigned_user_count=assigned).model_dump())


@router.get("/{role_id}")
async def get_access_role(
    request: Request,
    role_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    service = CustomAccessRoleService(db_session)
    try:
        role = await service.get_role(role_id)
    except CustomAccessRoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    assigned = await service.assigned_user_count(role.id)
    return _envelope(request, CustomAccessRoleDetail.from_model(role, assigned_user_count=assigned).model_dump())


@router.patch("/{role_id}")
async def update_access_role(
    request: Request,
    role_id: int,
    body: UpdateCustomAccessRoleRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = CustomAccessRoleService(db_session)
    try:
        role = await service.update_role(
            role_id,
            name=body.name,
            description=body.description,
            permissions=body.permissions,
            is_active=body.is_active,
            actor=_actor(current),
        )
    except CustomAccessRoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DuplicateAccessRoleNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    assigned = await service.assigned_user_count(role.id)
    return _envelope(request, CustomAccessRoleDetail.from_model(role, assigned_user_count=assigned).model_dump())


@router.delete("/{role_id}")
async def delete_access_role(
    request: Request,
    role_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = CustomAccessRoleService(db_session)
    try:
        await service.delete_role(role_id, actor=_actor(current))
    except CustomAccessRoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CustomAccessRoleInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, {"success": True})
