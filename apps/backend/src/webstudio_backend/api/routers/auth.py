"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.client_context import client_device_label, client_ip, client_user_agent
from webstudio_backend.api.dependencies.auth import CurrentUserDep
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.api.schemas.user import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    LogoutRequest,
    MainAdminRecoverPasswordRequest,
    MainAdminRecoverPasswordResponse,
    PasswordRecoveryPolicyResponse,
    RefreshRequest,
    TokenResponse,
    UserSummary,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import DbSessionDep, get_app_settings
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.repositories.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRecoveryKeyError,
    InvalidRefreshTokenError,
    MainAdminNotFoundError,
    RefreshTokenReuseError,
    SystemNotInitializedError,
)
from webstudio_backend.services.authentication_service import AuthenticationService
from webstudio_backend.services.main_admin_recovery_service import MainAdminRecoveryService
from webstudio_backend.services.security_service import SecurityService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _token_response(request: Request, pair) -> dict:
    payload = TokenResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        token_type=pair.token_type,
        expires_in=pair.expires_in,
        session_id=pair.session_id,
        user=UserSummary.from_model(pair.user),
    )
    return _envelope(request, payload.model_dump())


@router.post("/login")
async def login(
    request: Request,
    body: LoginRequest,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    service = AuthenticationService(db_session, settings)
    try:
        pair = await service.login(
            username=body.username,
            password=body.password,
            remember_me=body.remember_me,
            ip_address=client_ip(request),
            user_agent=client_user_agent(request),
            device_label=client_device_label(request, body.device_label),
        )
    except SystemNotInitializedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_LOCKED",
                "message": str(exc),
                "locked_until": exc.locked_until.isoformat() if exc.locked_until else None,
            },
        ) from exc
    except AccountDisabledError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _token_response(request, pair)


@router.post("/refresh")
async def refresh_token_endpoint(
    request: Request,
    body: RefreshRequest,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    service = AuthenticationService(db_session, settings)
    try:
        pair = await service.refresh(refresh_token=body.refresh_token)
    except RefreshTokenReuseError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except (InvalidRefreshTokenError, AccountDisabledError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _token_response(request, pair)


@router.post("/logout")
async def logout(
    request: Request,
    body: LogoutRequest,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    await AuthenticationService(db_session, settings).logout(
        user=current.user,
        refresh_token=body.refresh_token,
    )
    return _envelope(request, {"success": True})


@router.post("/logout-all")
async def logout_all(
    request: Request,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    count = await AuthenticationService(db_session, settings).logout_all(current.user)
    return _envelope(request, {"success": True, "revoked_sessions": count})


@router.get("/sessions")
async def list_sessions(
    request: Request,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
    refresh_token: str | None = None,
) -> dict:
    auth_service = AuthenticationService(db_session, settings)
    current_session_id = None
    if refresh_token:
        current_session_id = await auth_service.resolve_session_id(refresh_token)
    sessions = await SecurityService(db_session, settings).list_active_sessions(
        current.user,
        current_session_id=current_session_id,
    )
    return _envelope(
        request,
        [
            {
                "id": session.id,
                "device_label": session.device_label,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "remember_me": session.remember_me,
                "created_at": session.created_at.isoformat(),
                "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
                "expires_at": session.expires_at.isoformat(),
                "is_current": session.is_current,
            }
            for session in sessions
        ],
    )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    request: Request,
    session_id: int,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    service = SecurityService(db_session, settings)
    try:
        await service.revoke_session(current.user, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _envelope(request, {"success": True})


@router.get("/me")
async def current_user(request: Request, current: CurrentUserDep) -> dict:
    return _envelope(
        request,
        CurrentUserResponse.from_model(current.user, permissions=current.permissions).model_dump(),
    )


@router.get("/session-policy")
async def session_policy(
    request: Request,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository

    timeout = await SystemSettingRepository(db_session).get_int("session_timeout_minutes", default=15)
    return _envelope(request, {"session_timeout_minutes": timeout})


@router.post("/change-password")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current: CurrentUserDep,
    db_session: AsyncSession = DbSessionDep,
    settings: Settings = Depends(get_app_settings),
) -> dict:
    service = AuthenticationService(db_session, settings)
    try:
        await service.change_password(
            user=current.user,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return _envelope(request, {"success": True})


@router.get("/password-recovery-policy")
async def password_recovery_policy(
    request: Request,
    role: str | None = None,
) -> dict:
    message = MainAdminRecoveryService.password_recovery_message_for_role(role)
    return _envelope(request, PasswordRecoveryPolicyResponse(**message).model_dump())


@router.post("/main-admin/recover-password")
async def recover_main_admin_password(
    request: Request,
    body: MainAdminRecoverPasswordRequest,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = MainAdminRecoveryService(db_session)
    try:
        result = await service.recover_password(
            recovery_key=body.recovery_key,
            new_password=body.new_password,
            confirm_password=body.confirm_password,
        )
    except SystemNotInitializedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except InvalidRecoveryKeyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except MainAdminNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    response = MainAdminRecoverPasswordResponse(recovery_key=result.new_recovery_key)
    return _envelope(request, response.model_dump())
