"""Security monitoring and session administration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.models.refresh_token import RefreshToken
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.login_event_repository import LoginEventRepository
from webstudio_backend.infrastructure.repositories.refresh_token_repository import RefreshTokenRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.services.audit_log_presenter import audit_severity, extract_security_event
from webstudio_backend.services.password_policy_service import PasswordPolicyService


@dataclass(frozen=True, slots=True)
class ActiveSessionView:
    id: int
    device_label: str | None
    ip_address: str | None
    user_agent: str | None
    remember_me: bool
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    is_current: bool


@dataclass(frozen=True, slots=True)
class LockedUserView:
    id: int
    username: str
    display_name: str | None
    locked_until: datetime | None
    failed_login_count: int


@dataclass(frozen=True, slots=True)
class LoginEventView:
    id: int
    username: str
    success: bool
    failure_reason: str | None
    ip_address: str | None
    device_label: str | None
    created_at: datetime


class SecurityService:
    def __init__(self, session: AsyncSession, app_settings: Settings) -> None:
        self._session = session
        self._app_settings = app_settings
        self._users = UserRepository(session)
        self._sessions = RefreshTokenRepository(session)
        self._login_events = LoginEventRepository(session)
        self._settings = SystemSettingRepository(session)
        self._password_policy = PasswordPolicyService(session)
        self._audit_logs = AuditLogRepository(session)

    async def list_active_sessions(
        self,
        user: User,
        *,
        current_session_id: int | None = None,
    ) -> list[ActiveSessionView]:
        tokens = await self._sessions.list_active_for_user(user.id)
        return [
            ActiveSessionView(
                id=token.id,
                device_label=token.device_label,
                ip_address=token.ip_address,
                user_agent=token.user_agent,
                remember_me=token.remember_me,
                created_at=token.created_at,
                last_used_at=token.last_used_at,
                expires_at=token.expires_at,
                is_current=current_session_id is not None and token.id == current_session_id,
            )
            for token in tokens
        ]

    async def revoke_session(self, user: User, session_id: int) -> None:
        from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder

        token = await self._sessions.get_active_for_user(user.id, session_id)
        if token is None:
            raise ValueError("Session not found")
        await self._sessions.revoke(token)
        await AuditRecorder(self._session).record_session_revoked(user, session_id=session_id)

    async def revoke_all_sessions(self, user_id: int) -> int:
        tokens = await self._sessions.list_active_for_user(user_id)
        await self._sessions.revoke_all_for_user(user_id)
        return len(tokens)

    async def get_dashboard(self, *, viewer: User) -> dict:
        from webstudio_backend.infrastructure.database.repositories.pagination import PageParams

        policy = await self._password_policy.get_policy()
        main_admin = await self._users.get_main_admin()
        locked_users = await self._list_locked_users()
        recent_events = await self._login_events.list_recent(limit=25)
        active_sessions = await self._sessions.list_active_for_user(viewer.id)
        org_session_count = await self._count_org_active_sessions()
        security_audits = await self._audit_logs.search_enriched(
            AuditLogSearchFilters(security_only=True),
            PageParams(page=1, page_size=15),
        )
        recent_security_events = [
            {
                "id": str(row.audit_log.id),
                "description": row.audit_log.description,
                "severity": audit_severity(row.audit_log),
                "security_event": extract_security_event(row.audit_log),
                "actor_display_name": row.audit_log.actor_display_name,
                "created_at": row.audit_log.created_at.isoformat(),
            }
            for row in security_audits.items
        ]
        critical_alerts = [
            event for event in recent_security_events if event["severity"] == "critical"
        ]

        return {
            "session_timeout_minutes": await self._settings.get_int("session_timeout_minutes", default=15),
            "active_session_count": len(active_sessions),
            "org_active_session_count": org_session_count,
            "active_sessions": [
                {
                    "id": session.id,
                    "device_label": session.device_label,
                    "ip_address": session.ip_address,
                    "remember_me": session.remember_me,
                    "created_at": session.created_at.isoformat(),
                    "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
                    "expires_at": session.expires_at.isoformat(),
                }
                for session in active_sessions
            ],
            "locked_users": [
                {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "locked_until": user.locked_until.isoformat() if user.locked_until else None,
                    "failed_login_count": user.failed_login_count,
                }
                for user in locked_users
            ],
            "failed_logins_24h": await self._login_events.failed_since_hours(24),
            "password_policy": PasswordPolicyService.compliance_summary(policy),
            "recovery": {
                "configured": bool(main_admin and main_admin.recovery_key_hash),
                "last_used_at": (
                    main_admin.recovery_key_last_used_at.isoformat()
                    if main_admin and main_admin.recovery_key_last_used_at
                    else None
                ),
            },
            "recent_login_events": [
                {
                    "id": event.id,
                    "username": event.username,
                    "success": event.success,
                    "failure_reason": event.failure_reason,
                    "ip_address": event.ip_address,
                    "device_label": event.device_label,
                    "created_at": event.created_at.isoformat(),
                }
                for event in recent_events
            ],
            "jwt_access_token_ttl_minutes": self._app_settings.access_token_ttl_minutes,
            "jwt_refresh_token_ttl_days": self._app_settings.refresh_token_ttl_days,
            "recent_security_events": recent_security_events,
            "critical_alerts": critical_alerts,
        }

    async def _count_org_active_sessions(self) -> int:
        from sqlalchemy import func, select

        from webstudio_backend.infrastructure.database.models.refresh_token import RefreshToken

        now = datetime.now(UTC)
        result = await self._session.execute(
            select(func.count()).select_from(RefreshToken).where(
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            ),
        )
        return int(result.scalar_one())

    async def _list_locked_users(self) -> list[User]:
        from sqlalchemy import select

        now = datetime.now(UTC)
        result = await self._session.execute(
            select(User).where(User.locked_until.is_not(None), User.locked_until > now),
        )
        return list(result.scalars().all())

    @staticmethod
    def session_label(token: RefreshToken) -> str:
        if token.device_label:
            return token.device_label
        if token.user_agent:
            return token.user_agent[:64]
        return "Unknown device"
