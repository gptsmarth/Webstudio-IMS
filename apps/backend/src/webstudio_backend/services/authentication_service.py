"""Authentication service — login, refresh, logout, sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import NotificationSeverity
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.exceptions import (
    AccountDisabledError,
    AccountLockedError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
    SessionIdleTimeoutError,
    SystemNotInitializedError,
)
from webstudio_backend.infrastructure.repositories.login_event_repository import (
    LoginEventRepository,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.jwt import create_access_token
from webstudio_backend.infrastructure.security.password import hash_password, verify_password
from webstudio_backend.infrastructure.security.tokens import (
    generate_refresh_token,
    hash_refresh_token,
)
from webstudio_backend.services.password_policy_service import PasswordPolicyService
from webstudio_backend.services.permission_resolver import PermissionResolver
from webstudio_backend.services.security_alert_service import SecurityAlertService


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: User
    session_id: int


class AuthenticationService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._refresh_tokens = RefreshTokenRepository(session)
        self._system_settings = SystemSettingRepository(session)
        self._login_events = LoginEventRepository(session)
        self._password_policy = PasswordPolicyService(session)
        self._recorder = AuditRecorder(session)

    async def login(
        self,
        *,
        username: str,
        password: str,
        remember_me: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> TokenPair:
        if not await self._system_settings.is_system_initialized():
            raise SystemNotInitializedError()

        user = await self._users.get_by_username(username)
        if user is None or user.password_hash is None:
            await self._record_login_failure(
                username, "invalid_credentials", ip_address, user_agent, device_label
            )
            raise InvalidCredentialsError()

        if user.status.value == "disabled" or user.archived_at is not None:
            await self._record_login_failure(
                username,
                "account_disabled",
                ip_address,
                user_agent,
                device_label,
                user_id=user.id,
            )
            raise AccountDisabledError()

        if user.locked_until and user.locked_until > datetime.now(UTC):
            await self._record_login_failure(
                username,
                "account_locked",
                ip_address,
                user_agent,
                device_label,
                user_id=user.id,
            )
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
            locked_before = user.locked_until is not None and user.locked_until > datetime.now(UTC)
            user = await self._users.record_failed_login(
                user,
                lockout_threshold=threshold,
                lockout_minutes=minutes,
            )
            locked_after = user.locked_until is not None and user.locked_until > datetime.now(UTC)
            if locked_after and not locked_before:
                await self._recorder.record_account_locked(
                    user,
                    locked_until=user.locked_until.isoformat() if user.locked_until else "",
                )
                await SecurityAlertService(self._session).emit(
                    title="Account locked",
                    message=f"User '{user.username}' was locked after repeated failed login attempts.",
                    severity=NotificationSeverity.ERROR,
                )
            await self._record_login_failure(
                username,
                "invalid_credentials",
                ip_address,
                user_agent,
                device_label,
                user_id=user.id,
            )
            raise InvalidCredentialsError()

        await self._users.record_successful_login(user)
        await self._recorder.record_auth_login_success(user)
        await self._login_events.record(
            username=user.username,
            success=True,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
        )
        return await self._issue_tokens(
            user,
            remember_me=remember_me,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
        )

    async def refresh(self, *, refresh_token: str) -> TokenPair:
        token_hash = hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is None:
            raise InvalidRefreshTokenError()
        if stored.revoked_at is not None:
            reuse_user = await self._users.get_by_id(stored.user_id)
            if reuse_user is not None:
                await self._recorder.record_token_refresh_reuse(reuse_user)
                await SecurityAlertService(self._session).emit(
                    title="Suspicious session activity",
                    message=f"Refresh token reuse detected for user '{reuse_user.username}'. All sessions were revoked.",
                    severity=NotificationSeverity.ERROR,
                )
            await self._refresh_tokens.revoke_family(stored)
            raise RefreshTokenReuseError()
        if stored.expires_at <= datetime.now(UTC):
            raise InvalidRefreshTokenError()

        user = await self._users.get_by_id(stored.user_id)
        if user is None or user.status.value == "disabled" or user.archived_at is not None:
            raise AccountDisabledError()

        timeout_minutes = await self._system_settings.get_int("session_timeout_minutes", default=15)
        last_activity = stored.last_used_at or stored.created_at
        idle_delta = datetime.now(UTC) - last_activity
        if idle_delta > timedelta(minutes=timeout_minutes):
            if user is not None:
                await self._refresh_tokens.revoke(stored)
                await self._recorder.record_session_idle_timeout(
                    user,
                    session_id=stored.id,
                    idle_minutes=timeout_minutes,
                )
                await self._login_events.record(
                    username=user.username,
                    success=False,
                    user_id=user.id,
                    failure_reason="session_idle_timeout",
                    ip_address=stored.ip_address,
                    user_agent=stored.user_agent,
                    device_label=stored.device_label,
                )
            raise SessionIdleTimeoutError()

        await self._refresh_tokens.touch(stored)

        new_refresh = generate_refresh_token()
        expires_at = await self._refresh_expiry(remember_me=stored.remember_me)
        new_stored = await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=expires_at,
            ip_address=stored.ip_address,
            user_agent=stored.user_agent,
            device_label=stored.device_label,
            remember_me=stored.remember_me,
        )
        await self._refresh_tokens.revoke(stored, replaced_by_id=new_stored.id)

        access_token, expires_in = await self._create_access_token(user)
        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
            session_id=new_stored.id,
        )

    async def logout(self, *, user: User, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is not None and stored.revoked_at is None:
            await self._refresh_tokens.revoke(stored)
        await self._recorder.record_auth_logout(user)

    async def logout_all(self, user: User) -> int:
        tokens = await self._refresh_tokens.list_active_for_user(user.id)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_auth_logout(user, all_sessions=True)
        return len(tokens)

    async def change_password(
        self,
        *,
        user: User,
        current_password: str | None,
        new_password: str,
    ) -> None:
        await self._password_policy.validate(new_password)
        await self._password_policy.ensure_not_reused(
            user.id, new_password, current_hash=user.password_hash
        )
        if not user.must_change_password:
            if current_password is None or user.password_hash is None:
                raise InvalidCredentialsError()
            if not verify_password(user.password_hash, current_password):
                raise InvalidCredentialsError()

        from webstudio_backend.infrastructure.audit.audit_actor import AuditActor

        new_hash = hash_password(new_password)
        await self._users.set_password(
            user,
            new_hash,
            must_change_password=False,
            actor_id=user.id,
        )
        await self._password_policy.record_password(user.id, new_hash)
        await self._refresh_tokens.revoke_all_for_user(user.id)
        await self._recorder.record_user_update(
            user,
            field_name="password",
            old_value={"password_changed": False},
            new_value={"password_changed": True},
            actor=AuditActor(
                user_id=user.id,
                display_name=user.display_name or user.username,
                role=user.role.value,
            ),
            description="Password changed",
        )

    async def _issue_tokens(
        self,
        user: User,
        *,
        remember_me: bool = False,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> TokenPair:
        access_token, expires_in = await self._create_access_token(user)
        refresh_token = generate_refresh_token()
        expires_at = await self._refresh_expiry(remember_me=remember_me)
        stored = await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
            remember_me=remember_me,
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user,
            session_id=stored.id,
        )

    async def _create_access_token(self, user: User) -> tuple[str, int]:
        permissions = await PermissionResolver(self._session).resolve_for_user(user)
        return create_access_token(
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

    async def _refresh_expiry(self, *, remember_me: bool) -> datetime:
        if remember_me:
            days = await self._system_settings.get_int("remember_me_ttl_days", default=30)
        else:
            days = self._settings.refresh_token_ttl_days
        return datetime.now(UTC) + timedelta(days=days)

    async def _record_login_failure(
        self,
        username: str,
        reason: str,
        ip_address: str | None,
        user_agent: str | None,
        device_label: str | None,
        *,
        user_id: int | None = None,
    ) -> None:
        await self._recorder.record_auth_login_failure(
            username,
            failure_reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
        )
        await self._login_events.record(
            username=username,
            success=False,
            user_id=user_id,
            failure_reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            device_label=device_label,
        )

    async def resolve_session_id(self, refresh_token: str) -> int | None:
        token_hash = hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        return stored.id if stored is not None else None
