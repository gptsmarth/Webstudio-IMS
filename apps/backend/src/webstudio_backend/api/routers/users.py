"""User management API endpoints."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    UsersActivateDep,
    UsersCreateDep,
    UsersDeactivateDep,
    UsersEditDep,
    UsersResetPasswordDep,
    UsersViewDep,
)
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.user import (
    AssignUserAccessRequest,
    CreateUserRequest,
    ResetPasswordRequest,
    RolePermissionsEntry,
    RolePermissionsResponse,
    UpdateUserRequest,
    UpdateUserRoleRequest,
    UserDetail,
    UserSummary,
    access_label_for_user,
)
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.permissions import permissions_for_role
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import UserRole, UserStatus
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateUsernameError,
    LastMainAdminError,
    SelfMainAdminDisableError,
    UserNotFoundError,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import RefreshTokenRepository
from webstudio_backend.services.custom_access_role_service import CustomAccessRoleNotFoundError, CustomAccessRoleService
from webstudio_backend.services.permission_resolver import PermissionResolver
from webstudio_backend.services.user_admin_service import UserAdminExtras, UserAdminService
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
    return build_page_meta(page, page_size, total_items, total_pages)


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


def _extras_payload(extras: UserAdminExtras, *, include_detail: bool = False) -> dict[str, object]:
    payload: dict[str, object] = {
        "failed_login_count": extras.failed_login_count,
        "is_locked": extras.is_locked,
        "is_archived": extras.is_archived,
        "active_session_count": extras.active_session_count,
        "password_age_days": extras.password_age_days,
        "created_by_display_name": extras.created_by_display_name,
    }
    if include_detail:
        payload.update(
            {
                "locked_until": extras.locked_until,
                "password_changed_at": extras.password_changed_at,
                "created_by_user_id": extras.created_by_user_id,
                "archived_at": extras.archived_at,
            },
        )
    return payload


def _serialize_summary(
    user: User,
    extras: UserAdminExtras,
    *,
    custom_role_name: str | None = None,
) -> dict:
    payload = UserSummary.from_model_with_extras(user, _extras_payload(extras)).model_dump()
    payload["custom_access_role_id"] = user.custom_access_role_id
    payload["custom_access_role_name"] = custom_role_name
    payload["access_label"] = access_label_for_user(user, custom_role_name=custom_role_name)
    return payload


def _serialize_detail(
    user: User,
    extras: UserAdminExtras,
    *,
    permissions: list[str],
    custom_role_name: str | None = None,
    sessions: list[dict[str, object]] | None = None,
    login_events: list[dict[str, object]] | None = None,
) -> dict:
    detail = UserDetail.from_model_with_extras(
        user,
        _extras_payload(extras, include_detail=True),
        permissions=permissions,
        sessions=sessions,
        login_events=login_events,
    ).model_dump()
    detail["custom_access_role_id"] = user.custom_access_role_id
    detail["custom_access_role_name"] = custom_role_name
    detail["access_label"] = access_label_for_user(user, custom_role_name=custom_role_name)
    return detail


async def _custom_role_name_map(db_session: AsyncSession, users: list[User]) -> dict[int, str]:
    role_ids = {user.custom_access_role_id for user in users if user.custom_access_role_id is not None}
    if not role_ids:
        return {}
    roles = await CustomAccessRoleService(db_session).list_roles(include_inactive=True)
    return {role.id: role.name for role in roles if role.id in role_ids}


@router.get("")
async def list_users(
    request: Request,
    current: UsersViewDep,
    db_session: AsyncSession = DbSessionDep,
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    role: UserRole | None = None,
    search: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    sort_field: str = Query(default="username"),
    sort_direction: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    result = await UserService(db_session).list_users(
        PageParams(page=page, page_size=page_size),
        status=status_filter,
        role=role,
        search=search,
        created_from=created_from,
        created_to=created_to,
        sort_field=sort_field,
        sort_direction=sort_direction,
    )
    admin_service = UserAdminService(db_session)
    user_ids = [user.id for user in result.items]
    session_counts = await RefreshTokenRepository(db_session).count_active_by_user_ids(user_ids)
    extras_map = await admin_service.batch_extras_for_users(result.items, session_counts)
    role_names = await _custom_role_name_map(db_session, result.items)
    return _envelope(
        request,
        [
            _serialize_summary(
                user,
                extras_map[user.id],
                custom_role_name=role_names.get(user.custom_access_role_id) if user.custom_access_role_id else None,
            )
            for user in result.items
        ],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/role-permissions")
async def list_role_permissions(
    request: Request,
    current: UsersViewDep,
) -> dict:
    human_roles = (UserRole.MAIN_ADMIN, UserRole.ADMIN, UserRole.SALESPERSON)
    payload = RolePermissionsResponse(
        roles=[
            RolePermissionsEntry(role=role, permissions=permissions_for_role(role))
            for role in human_roles
        ],
    )
    return _envelope(request, payload.model_dump())


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    body: CreateUserRequest,
    current: UsersCreateDep,
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
    current: UsersViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        user = await UserService(db_session).get_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    admin_service = UserAdminService(db_session)
    extras = await admin_service.extras_for_user(user)
    sessions = await admin_service.list_sessions_for_user(user_id)
    login_events = await admin_service.list_login_events_for_user(user_id)
    role_names = await _custom_role_name_map(db_session, [user])
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(
        request,
        _serialize_detail(
            user,
            extras,
            permissions=permissions,
            custom_role_name=role_names.get(user.custom_access_role_id) if user.custom_access_role_id else None,
            sessions=sessions,
            login_events=login_events,
        ),
    )


@router.patch("/{user_id}")
async def update_user(
    request: Request,
    user_id: int,
    body: UpdateUserRequest,
    current: UsersEditDep,
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
    current: UsersEditDep,
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
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(request, UserDetail.from_model(user, permissions=permissions).model_dump())


@router.patch("/{user_id}/access")
async def assign_user_access(
    request: Request,
    user_id: int,
    body: AssignUserAccessRequest,
    current: UsersEditDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.assign_access(
            user_id,
            access_type=body.access_type,
            role=body.role,
            custom_role_id=body.custom_role_id,
            actor=_actor(current),
        )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CustomAccessRoleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(request, UserDetail.from_model(user, permissions=permissions).model_dump())


@router.post("/{user_id}/reset-password")
async def reset_password(
    request: Request,
    user_id: int,
    body: ResetPasswordRequest,
    current: UsersResetPasswordDep,
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
    current: UsersDeactivateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.disable_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastMainAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SelfMainAdminDisableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.post("/{user_id}/enable")
async def enable_user(
    request: Request,
    user_id: int,
    current: UsersActivateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.enable_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, UserDetail.from_model(user).model_dump())


@router.post("/{user_id}/unlock")
async def unlock_user(
    request: Request,
    user_id: int,
    current: UsersEditDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.unlock_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    extras = await UserAdminService(db_session).extras_for_user(user)
    role_names = await _custom_role_name_map(db_session, [user])
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(
        request,
        _serialize_detail(
            user,
            extras,
            permissions=permissions,
            custom_role_name=role_names.get(user.custom_access_role_id) if user.custom_access_role_id else None,
        ),
    )


@router.post("/{user_id}/logout-all")
async def force_logout_user(
    request: Request,
    user_id: int,
    current: UsersEditDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        revoked = await service.force_logout_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, {"success": True, "sessions_revoked": revoked})


@router.post("/{user_id}/archive")
async def archive_user(
    request: Request,
    user_id: int,
    current: UsersDeactivateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.archive_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LastMainAdminError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SelfMainAdminDisableError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    extras = await UserAdminService(db_session).extras_for_user(user)
    role_names = await _custom_role_name_map(db_session, [user])
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(
        request,
        _serialize_detail(
            user,
            extras,
            permissions=permissions,
            custom_role_name=role_names.get(user.custom_access_role_id) if user.custom_access_role_id else None,
        ),
    )


@router.post("/{user_id}/restore")
async def restore_user(
    request: Request,
    user_id: int,
    current: UsersActivateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = UserService(db_session)
    try:
        user = await service.restore_user(user_id, actor=_actor(current))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    extras = await UserAdminService(db_session).extras_for_user(user)
    role_names = await _custom_role_name_map(db_session, [user])
    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return _envelope(
        request,
        _serialize_detail(
            user,
            extras,
            permissions=permissions,
            custom_role_name=role_names.get(user.custom_access_role_id) if user.custom_access_role_id else None,
        ),
    )
