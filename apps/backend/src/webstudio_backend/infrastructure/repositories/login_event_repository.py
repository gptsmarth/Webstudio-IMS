"""Login event persistence for authentication monitoring."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.login_event import LoginEvent
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class LoginEventRepository(SqlAlchemyRepository[LoginEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LoginEvent)

    async def record(
        self,
        *,
        username: str,
        success: bool,
        user_id: int | None = None,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
    ) -> LoginEvent:
        return await self.add(
            LoginEvent(
                user_id=user_id,
                username=username,
                success=success,
                failure_reason=failure_reason,
                ip_address=ip_address,
                user_agent=user_agent,
                device_label=device_label,
            ),
        )

    async def list_recent(self, *, limit: int = 50) -> list[LoginEvent]:
        result = await self._session.execute(
            select(LoginEvent).order_by(LoginEvent.created_at.desc()).limit(limit),
        )
        return list(result.scalars().all())

    async def count_failed_since(self, since: datetime) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(LoginEvent)
            .where(LoginEvent.success.is_(False), LoginEvent.created_at >= since),
        )
        return int(result.scalar_one())

    async def count_locked_users(self) -> int:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(func.count())
            .select_from(User)
            .where(User.locked_until.is_not(None), User.locked_until > now),
        )
        return int(result.scalar_one())

    async def failed_since_hours(self, hours: int = 24) -> int:
        since = datetime.now(UTC) - timedelta(hours=hours)
        return await self.count_failed_since(since)
