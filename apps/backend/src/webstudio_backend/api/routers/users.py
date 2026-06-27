"""User management API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import MainAdminDep
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.user import (
    CreateUserRequest,
    ResetPasswordRequest,
    UpdateUserRequest,
    UpdateUserRoleRequest,
    UserDetail,
    UserSummary,
)
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import UserRole, UserStatus
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateUsernameError,
    LastMainAdminError,
    UserNotFoundError,
)
from webstudio_backend.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


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


def _actor(current: MainAdminDep) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


@router.get("")
async def list_users(
    request: Request,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    role: UserRole | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    result = await UserService(db_session).list_users(
        PageParams(page=page, page_size=page_size),
        status=status_filter,
        role=role,
        search=search,
    )
    return _envelope(
        request,
        [UserSummary.from_model(user).model_dump() for user in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.create_user(
            username=body.username,
            role=body.role,
            temporary_password=body.temporary_password,
            display_name=body.display_name,
            actor=_actor(current),
        )
    except DuplicateUsernameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.get("/{user_id}")
async def get_user(
    request: Request,
    user_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        user = await UserService(db_session).get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.patch("/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    body: UpdateUserRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    if body.display_name is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No fields to update")
    service = UserService(db_session)
    try:
        user = await service.update_display_name(
            user_id,
            display_name=body.display_name,
            actor=_actor(current),
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.patch("/{user_id}/role")
async def update_user_role(
    request: Request,
    user_id: int,
    body: UpdateUserRoleRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.update_role(user_id, role=body.role, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastMainAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.post("/{user_id}/reset-password")
async def reset_password(
    request: Request,
    user_id: int,
    body: ResetPasswordRequest,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        await service.reset_password(
            user_id,
            temporary_password=body.temporary_password,
            actor=_actor(current),
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, {"success": True})


@router.post("/{user_id}/disable")
async def disable_user(
    request: Request,
    user_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.disable_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastMainAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.post("/{user_id}/enable")
async def enable_user(
    request: Request,
    user_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.enable_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())
