"""Authentication dependencies and current user resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.dependencies import DbSessionDep, get_app_settings
from webstudio_backend.core.permissions import permissions_for_role, role_has_permission
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.jwt import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user: User
    permissions: list[str]


async def get_current_user(
    request: Request,
    db_session: AsyncSession = DbSessionDep,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_app_settings),
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_access_token(
            credentials.credentials,
            secret=settings.jwt_secret,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user_id = int(payload["sub"])
    user = await UserRepository(db_session).get_by_id(user_id)
    if user is None or user.status.value == "disabled":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if int(payload.get("token_version", -1)) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return AuthenticatedUser(user=user, permissions=permissions_for_role(user.role))


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]


def require_permission(permission: str):
    async def _checker(current: CurrentUserDep) -> AuthenticatedUser:
        if not role_has_permission(current.user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current

    return _checker


def require_main_admin(current: CurrentUserDep) -> AuthenticatedUser:
    if current.user.role != UserRole.MAIN_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Main Admin required")
    return current


MainAdminDep = Annotated[AuthenticatedUser, Depends(require_main_admin)]

AuditReadDep = Annotated[AuthenticatedUser, Depends(require_permission("audit:read"))]

SettingsReadDep = Annotated[AuthenticatedUser, Depends(require_permission("settings:read"))]
SettingsWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("settings:write"))]
TallyDashboardDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:dashboard"))]
TallySyncDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:sync"))]
