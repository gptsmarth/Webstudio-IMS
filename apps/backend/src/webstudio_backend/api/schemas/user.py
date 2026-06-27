"""User and auth API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from webstudio_backend.core.permissions import permissions_for_role
from webstudio_backend.infrastructure.database.enums import ThemePreference, UserRole, UserStatus
from webstudio_backend.infrastructure.database.models.user import User


class UserSummary(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: UserRole
    status: UserStatus
    must_change_password: bool = False
    theme_preference: ThemePreference | None = None
    last_login_at: datetime | None = None

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
        )


class UserDetail(UserSummary):
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, user: User) -> UserDetail:
        base = UserSummary.from_model(user)
        return cls(
            **base.model_dump(),
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class CurrentUserResponse(UserSummary):
    permissions: list[str] = Field(default_factory=list)

    @classmethod
    def from_model(cls, user: User) -> CurrentUserResponse:
        base = UserSummary.from_model(user)
        return cls(
            **base.model_dump(),
            permissions=permissions_for_role(user.role),
        )


class LoginRequest(BaseModel):
    username: str
    password: str


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


class ResetPasswordRequest(BaseModel):
    temporary_password: str
