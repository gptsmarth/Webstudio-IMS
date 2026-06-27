"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

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
        pair = await service.login(username=body.username, password=body.password)
    except SystemNotInitializedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AccountLockedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
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


@router.get("/me")
async def current_user(request: Request, current: CurrentUserDep) -> dict:
    return _envelope(request, CurrentUserResponse.from_model(current.user).model_dump())


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
