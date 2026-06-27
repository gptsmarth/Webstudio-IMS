"""Authentication service — login, refresh, logout."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.core.permissions import permissions_for_role
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    SystemNotInitializedError,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.jwt import create_access_token
from webstudio_backend.infrastructure.security.password import verify_password
from webstudio_backend.infrastructure.security.tokens import generate_refresh_token, hash_refresh_token


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: User


class AuthenticationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._system_settings = SystemSettingRepository(session)
        self._recorder = AuditRecorder(session)

    async def login(self, *, username: str, password: str) -> TokenPair:
        if not await self._system_settings.is_system_initialized():
            raise SystemNotInitializedError()

        user = await self._users.get_by_username(username)
        if user is None or user.password_hash is None:
            await self._recorder.record_auth_login_failure(username)
            raise InvalidCredentialsError()

        if user.status.value == "disabled":
            raise AccountDisabledError()

        if user.locked_until and user.locked_until > datetime.now(UTC):
            raise AccountLockedError(user.locked_until)

        if not verify_password(user.password_hash, password):
            threshold = await self._system_settings.get_int(
                "lockout_threshold",
                default=self._settings.default_lockout_threshold,
            )
            minutes = await self._system_settings.get_int(
                "lockout_duration_minutes",
                default=self._settings.default_lockout_duration_minutes,
            )
            await self._users.record_failed_login(
                user,
                lockout_threshold=threshold,
                lockout_minutes=minutes,
            )
            await self._recorder.record_auth_login_failure(username)
            raise InvalidCredentialsError()

        await self._users.record_successful_login(user)
        await self._recorder.record_auth_login_success(user)
        return await self._issue_tokens(user)

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        token_hash = hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is None:
            raise InvalidRefreshTokenError()
        if stored.revoked_at is not None:
            await self._refresh_tokens.revoke_family(stored)
            raise RefreshTokenReuseError()
        if stored.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError()

        user = await self._users.get_by_id(stored.user_id)
        if user is None or user.status.value == "disabled":
            raise AccountDisabledError()

        new_refresh = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days)
        new_stored = await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=expires_at,
        )
        await self._refresh_tokens.revoke(stored, replaced_by_id=new_stored.id)

        permissions = permissions_for_role(user.role)
        access_token, expires_in = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            permissions=permissions,
            token_version=user.token_version,
            secret=self._settings.jwt_secret,
            issuer=self._settings.jwt_issuer,
            audience=self._settings.jwt_audience,
            expires_minutes=self._settings.access_token_ttl_minutes,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
        )

    async def logout(self, *, user: User, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is not None and stored.revoked_at is None:
            await self._refresh_tokens.revoke(stored)
        await self._recorder.record_auth_logout(user)

    async def change_password(
        self,
        *,
        user: User,
        current_password: str | None,
        new_password: str,
    ) -> None:
        from webstudio_backend.infrastructure.security.password import (
            hash_password,
            validate_password_strength,
        )

        validate_password_strength(new_password)
        if not user.must_change_password:
            if current_password is None or user.password_hash is None:
                raise InvalidCredentialsError()
            if not verify_password(user.password_hash, current_password):
                raise InvalidCredentialsError()

        from webstudio_backend.infrastructure.audit.audit_actor import AuditActor

        await self._users.set_password(
            user,
            hash_password(new_password),
            must_change_password=False,
            actor_id=user.id,
        )
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_update(
            user,
            field_name="password",
            old_value={"password_changed": False},
            new_value={"password_changed": True},
            actor=AuditActor(user_id=user.id, display_name=user.display_name or user.username, role=user.role.value),
            description="Password changed",
        )

    async def _issue_tokens(self, user: User) -> TokenPair:
        permissions = permissions_for_role(user.role)
        access_token, expires_in = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            permissions=permissions,
            token_version=user.token_version,
            secret=self._settings.jwt_secret,
            issuer=self._settings.jwt_issuer,
            audience=self._settings.jwt_audience,
            expires_minutes=self._settings.access_token_ttl_minutes,
        )
        refresh_token = generate_refresh_token()
        expires_at = datetime.now(UTC) + timedelta(days=self._settings.refresh_token_ttl_days)
        await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
        )
