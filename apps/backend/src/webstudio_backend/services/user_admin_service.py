"""User administration enrichment and session helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.login_event_repository import (
    LoginEventRepository,
)
from webstudio_backend.infrastructure.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.services.security_service import SecurityService


@dataclass(frozen=True, slots=True)
class UserAdminExtras:
    failed_login_count: int
    locked_until: datetime | None
    is_locked: bool
    active_session_count: int
    password_changed_at: datetime | None
    password_age_days: int | None
    created_by_user_id: int | None
    created_by_display_name: str | None
    archived_at: datetime | None
    is_archived: bool


class UserAdminService:
    def __init__(self, session: AsyncSession, app_settings: Settings | None = None) -> None:
        self._session = session
        self._settings = app_settings or get_settings()
        self._users = UserRepository(session)
        self._sessions = RefreshTokenRepository(session)
        self._login_events = LoginEventRepository(session)

    def _security(self) -> SecurityService:
        return SecurityService(self._session, self._settings)

    async def extras_for_user(self, user: User) -> UserAdminExtras:
        sessions = await self._sessions.list_active_for_user(user.id)
        created_by_name = await self._creator_name(user.created_by_user_id)
        return self._build_extras(user, len(sessions), created_by_name)

    async def batch_extras_for_users(
        self,
        users: list[User],
        session_counts: dict[int, int],
    ) -> dict[int, UserAdminExtras]:
        creator_ids = {user.created_by_user_id for user in users if user.created_by_user_id}
        creators: dict[int, str] = {}
        for creator_id in creator_ids:
            name = await self._creator_name(creator_id)
            if name:
                creators[creator_id] = name
        return {
            user.id: self._build_extras(
                user,
                session_counts.get(user.id, 0),
                creators.get(user.created_by_user_id) if user.created_by_user_id else None,
            )
            for user in users
        }

    async def _creator_name(self, user_id: int | None) -> str | None:
        if not user_id:
            return None
        creator = await self._users.get_by_id(user_id)
        return (creator.display_name or creator.username) if creator else None

    def _build_extras(
        self,
        user: User,
        active_session_count: int,
        created_by_name: str | None,
    ) -> UserAdminExtras:
        now = datetime.now(UTC)
        password_age_days = None
        if user.password_changed_at:
            password_age_days = max(0, (now - user.password_changed_at).days)
        locked_until = user.locked_until
        is_locked = locked_until is not None and locked_until > now
        return UserAdminExtras(
            failed_login_count=user.failed_login_count,
            locked_until=locked_until,
            is_locked=is_locked,
            active_session_count=active_session_count,
            password_changed_at=user.password_changed_at,
            password_age_days=password_age_days,
            created_by_user_id=user.created_by_user_id,
            created_by_display_name=created_by_name,
            archived_at=user.archived_at,
            is_archived=user.archived_at is not None,
        )

    async def list_sessions_for_user(self, user_id: int) -> list[dict]:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        service = self._security()
        sessions = await service.list_active_sessions(user)
        return [
            {
                "id": session.id,
                "device_label": session.device_label,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "remember_me": session.remember_me,
                "created_at": session.created_at.isoformat(),
                "last_used_at": session.last_used_at.isoformat() if session.last_used_at else None,
                "expires_at": session.expires_at.isoformat(),
            }
            for session in sessions
        ]

    async def list_login_events_for_user(self, user_id: int, *, limit: int = 20) -> list[dict]:
        from sqlalchemy import select

        from webstudio_backend.infrastructure.database.models.login_event import LoginEvent

        result = await self._session.execute(
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.created_at.desc())
            .limit(limit),
        )
        return [
            {
                "id": event.id,
                "username": event.username,
                "success": event.success,
                "failure_reason": event.failure_reason,
                "ip_address": event.ip_address,
                "device_label": event.device_label,
                "created_at": event.created_at.isoformat(),
            }
            for event in result.scalars().all()
        ]

    async def force_logout(self, user_id: int) -> int:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")
        return await self._security().revoke_all_sessions(user_id)
