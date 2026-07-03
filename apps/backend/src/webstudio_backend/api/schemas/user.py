"""User and auth API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from webstudio_backend.core.permissions import permissions_for_role
from webstudio_backend.infrastructure.database.enums import ThemePreference, UserRole, UserStatus
from webstudio_backend.infrastructure.database.models.user import User


def _builtin_role_label(role: UserRole) -> str:
    return {
        UserRole.MAIN_ADMIN: "Main Admin",
        UserRole.ADMIN: "Admin",
        UserRole.SALESPERSON: "Salesperson",
        UserRole.SERVICE_ACCOUNT: "Service Account",
    }.get(role, role.value)


def access_label_for_user(
    user: User,
    *,
    custom_role_name: str | None = None,
) -> str:
    if user.custom_access_role_id is not None and custom_role_name:
        return custom_role_name
    return _builtin_role_label(user.role)


class UserSummary(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: UserRole
    status: UserStatus
    must_change_password: bool = False
    theme_preference: ThemePreference | None = None
    last_login_at: datetime | None = None
    created_at: datetime | None = None
    failed_login_count: int = 0
    is_locked: bool = False
    is_archived: bool = False
    active_session_count: int = 0
    password_age_days: int | None = None
    created_by_display_name: str | None = None
    custom_access_role_id: int | None = None
    custom_access_role_name: str | None = None
    access_label: str | None = None

    @classmethod
    def from_model(cls, user: User) -> UserSummary:
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            status=user.status,
            must_change_password=user.must_change_password,
            theme_preference=user.theme_preference,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )

    @classmethod
    def from_model_with_extras(cls, user: User, extras: dict[str, object]) -> UserSummary:
        base = cls.from_model(user)
        merged = {**base.model_dump(), **extras}
        return cls(**{key: merged[key] for key in cls.model_fields})


class UserSessionSummary(BaseModel):
    id: int
    device_label: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    remember_me: bool = False
    created_at: str
    last_used_at: str | None = None
    expires_at: str


class UserLoginEventSummary(BaseModel):
    id: int
    username: str
    success: bool
    failure_reason: str | None = None
    ip_address: str | None = None
    device_label: str | None = None
    created_at: str


class UserDetail(UserSummary):
    created_at: datetime
    updated_at: datetime
    permissions: list[str] = Field(default_factory=list)
    locked_until: datetime | None = None
    password_changed_at: datetime | None = None
    created_by_user_id: int | None = None
    archived_at: datetime | None = None
    sessions: list[UserSessionSummary] = Field(default_factory=list)
    login_events: list[UserLoginEventSummary] = Field(default_factory=list)

    @classmethod
    def from_model(cls, user: User, *, permissions: list[str] | None = None) -> UserDetail:
        base = UserSummary.from_model(user)
        return cls(
            **base.model_dump(),
            updated_at=user.updated_at,
            permissions=permissions if permissions is not None else permissions_for_role(user.role),
        )

    @classmethod
    def from_model_with_extras(
        cls,
        user: User,
        extras: dict[str, object],
        *,
        permissions: list[str] | None = None,
        sessions: list[dict[str, object]] | None = None,
        login_events: list[dict[str, object]] | None = None,
    ) -> UserDetail:
        base = UserSummary.from_model_with_extras(user, extras)
        detail_fields = {
            "updated_at": user.updated_at,
            "permissions": (
                permissions if permissions is not None else permissions_for_role(user.role)
            ),
            "locked_until": extras.get("locked_until"),
            "password_changed_at": extras.get("password_changed_at"),
            "created_by_user_id": extras.get("created_by_user_id"),
            "archived_at": extras.get("archived_at"),
            "sessions": [UserSessionSummary.model_validate(item) for item in (sessions or [])],
            "login_events": [
                UserLoginEventSummary.model_validate(item) for item in (login_events or [])
            ],
        }
        return cls(**base.model_dump(), **detail_fields)


class RolePermissionsEntry(BaseModel):
    role: UserRole
    permissions: list[str]


class RolePermissionsResponse(BaseModel):
    roles: list[RolePermissionsEntry]


class CurrentUserResponse(UserSummary):
    permissions: list[str] = Field(default_factory=list)

    @classmethod
    def from_model(cls, user: User, *, permissions: list[str] | None = None) -> CurrentUserResponse:
        base = UserSummary.from_model(user)
        return cls(
            **base.model_dump(),
            permissions=permissions if permissions is not None else permissions_for_role(user.role),
        )


class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False
    device_label: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str | None = None
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: int | None = None
    user: UserSummary


class SetupStatusResponse(BaseModel):
    system_initialized: bool
    company_name: str | None = None
    awaiting_recovery_key_confirmation: bool = False


class SetupInitializeRequest(BaseModel):
    company_name: str
    main_admin_name: str
    username: str
    password: str
    confirm_password: str


class SetupInitializeResponse(BaseModel):
    system_initialized: bool = False
    company_name: str
    main_admin: UserSummary
    recovery_key: str


class SetupConfirmRecoveryKeyResponse(BaseModel):
    system_initialized: bool = True


class MainAdminRecoverPasswordRequest(BaseModel):
    recovery_key: str
    new_password: str
    confirm_password: str


class MainAdminRecoverPasswordResponse(BaseModel):
    success: bool = True
    recovery_key: str


class PasswordRecoveryPolicyResponse(BaseModel):
    self_service_available: bool
    message: str


class CreateUserRequest(BaseModel):
    username: str
    display_name: str | None = None
    role: UserRole
    temporary_password: str


class UpdateUserRequest(BaseModel):
    display_name: str | None = None


class UpdateUserRoleRequest(BaseModel):
    role: UserRole


class AssignUserAccessRequest(BaseModel):
    access_type: str = Field(pattern="^(builtin|custom)$")
    role: UserRole | None = None
    custom_role_id: int | None = None


class ResetPasswordRequest(BaseModel):
    temporary_password: str
