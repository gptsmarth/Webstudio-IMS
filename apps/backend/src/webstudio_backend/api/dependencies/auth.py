"""Authentication dependencies and current user resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.core.dependencies import DbSessionDep, get_app_settings
from webstudio_backend.core.permissions import (
    permissions_for_role,
    user_has_any_permission,
    user_has_permission,
)
from webstudio_backend.services.permission_resolver import PermissionResolver
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
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
    if user is None or user.status.value == "disabled" or user.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if int(payload.get("token_version", -1)) != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    permissions = await PermissionResolver(db_session).resolve_for_user(user)
    return AuthenticatedUser(user=user, permissions=permissions)


CurrentUserDep = Annotated[AuthenticatedUser, Depends(get_current_user)]


async def _audit_permission_denied(
    db_session: AsyncSession,
    request: Request,
    user: User,
    permission: str,
) -> None:
    path = request.url.path
    method = request.method
    recorder = AuditRecorder(db_session)
    await recorder.record_permission_denied(
        user=user,
        permission=permission,
        path=path,
        method=method,
    )


def require_permission(permission: str):
    async def _checker(
        request: Request,
        current: CurrentUserDep,
        db_session: AsyncSession = DbSessionDep,
    ) -> AuthenticatedUser:
        granted = set(current.permissions)
        if not user_has_permission(granted, permission):
            await _audit_permission_denied(db_session, request, current.user, permission)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current

    return _checker


def require_any_permission(*permissions: str):
    async def _checker(
        request: Request,
        current: CurrentUserDep,
        db_session: AsyncSession = DbSessionDep,
    ) -> AuthenticatedUser:
        granted = set(current.permissions)
        if not user_has_any_permission(granted, *permissions):
            await _audit_permission_denied(
                db_session,
                request,
                current.user,
                permissions[0] if permissions else "unknown",
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current

    return _checker


def require_main_admin(current: CurrentUserDep) -> AuthenticatedUser:
    if current.user.role != UserRole.MAIN_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Main Admin required")
    return current


MainAdminDep = Annotated[AuthenticatedUser, Depends(require_main_admin)]

# Inventory
InventoryViewDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:view"))]
InventoryCreateDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:create"))]
InventoryEditDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:edit"))]
InventoryTransferDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:transfer"))]
InventoryArchiveDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:archive"))]
InventoryRestoreDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:restore"))]

# Sales
SalesViewDep = Annotated[AuthenticatedUser, Depends(require_permission("sales:view"))]
SalesCreateDep = Annotated[AuthenticatedUser, Depends(require_permission("sales:create"))]

# Reports
ReportsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("reports:view"))]
ReportsExportDep = Annotated[AuthenticatedUser, Depends(require_permission("reports:export"))]

# Dashboard
DashboardViewDep = Annotated[AuthenticatedUser, Depends(require_permission("dashboard:view"))]

# Catalogue
BrandsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("brands:view"))]
# Stock browse and inventory screens need the full brand catalogue for users with inventory access.
BrandsOrInventoryViewDep = Annotated[
    AuthenticatedUser,
    Depends(
        require_any_permission("brands:view", "inventory:view", "inventory:create"),
    ),
]
BrandsCreateDep = Annotated[AuthenticatedUser, Depends(require_any_permission("brands:create", "brands:edit"))]
BrandsEditDep = Annotated[AuthenticatedUser, Depends(require_permission("brands:edit"))]
BrandsArchiveDep = Annotated[AuthenticatedUser, Depends(require_permission("brands:archive"))]

ProductModelsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:view"))]
ProductModelsOrInventoryViewDep = Annotated[
    AuthenticatedUser,
    Depends(
        require_any_permission(
            "product_models:view",
            "inventory:view",
            "inventory:create",
        ),
    ),
]
ProductModelsCreateDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:create"))]
ProductModelsEditDep = Annotated[
    AuthenticatedUser,
    Depends(
        require_any_permission(
            "product_models:edit",
            "product_models:selling_price:edit",
            "inventory:stock_edit",
        ),
    ),
]
ProductModelsArchiveDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:archive"))]
ProductModelsSellingPriceDep = Annotated[
    AuthenticatedUser,
    Depends(
        require_any_permission("product_models:selling_price:edit", "inventory:stock_edit"),
    ),
]

LocationsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("locations:view"))]
LocationsCreateDep = Annotated[AuthenticatedUser, Depends(require_permission("locations:create"))]
LocationsEditDep = Annotated[AuthenticatedUser, Depends(require_permission("locations:edit"))]
LocationsArchiveDep = Annotated[AuthenticatedUser, Depends(require_permission("locations:archive"))]

# Users
UsersViewDep = Annotated[AuthenticatedUser, Depends(require_permission("users:view"))]
UsersCreateDep = Annotated[AuthenticatedUser, Depends(require_permission("users:create"))]
UsersEditDep = Annotated[AuthenticatedUser, Depends(require_permission("users:edit"))]
UsersResetPasswordDep = Annotated[AuthenticatedUser, Depends(require_permission("users:reset_password"))]
UsersActivateDep = Annotated[AuthenticatedUser, Depends(require_permission("users:activate"))]
UsersDeactivateDep = Annotated[AuthenticatedUser, Depends(require_permission("users:deactivate"))]

# Audit
AuditViewDep = Annotated[AuthenticatedUser, Depends(require_permission("audit:view"))]
AuditLifecycleDep = Annotated[AuthenticatedUser, Depends(require_permission("audit:lifecycle"))]

# Notifications
NotificationsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("notifications:view"))]
NotificationsManageDep = Annotated[AuthenticatedUser, Depends(require_permission("notifications:manage"))]

# Settings
SettingsViewDep = Annotated[AuthenticatedUser, Depends(require_permission("settings:view"))]
SettingsModifyDep = Annotated[AuthenticatedUser, Depends(require_permission("settings:modify"))]

# Backup & recovery
BackupViewDep = Annotated[AuthenticatedUser, Depends(require_permission("backup:view"))]
BackupManageDep = Annotated[AuthenticatedUser, Depends(require_permission("backup:manage"))]
RestoreViewDep = Annotated[AuthenticatedUser, Depends(require_permission("restore:view"))]
RestoreExecuteDep = Annotated[AuthenticatedUser, Depends(require_permission("restore:execute"))]
BackupOrRestoreViewDep = Annotated[
    AuthenticatedUser,
    Depends(require_any_permission("backup:view", "restore:view")),
]

# Tally
TallyViewStatusDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:view_status"))]
TallyConfigureDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:configure"))]
TallyRunSyncDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:run_sync"))]
TallyRetrySyncDep = Annotated[AuthenticatedUser, Depends(require_permission("tally:retry_sync"))]

# Backward-compatible aliases (prefer module deps above in new code)
AuditReadDep = AuditViewDep
SettingsReadDep = SettingsViewDep
SettingsWriteDep = SettingsModifyDep
TallyDashboardDep = TallyViewStatusDep
TallySyncDep = TallyRunSyncDep
