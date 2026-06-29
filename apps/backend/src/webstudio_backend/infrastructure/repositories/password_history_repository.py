"""Password history persistence."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.password_history import PasswordHistory
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository
from webstudio_backend.infrastructure.security.password import verify_password


class PasswordHistoryRepository(SqlAlchemyRepository[PasswordHistory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PasswordHistory)

    async def list_recent_hashes(self, user_id: int, *, limit: int) -> list[str]:
        result = await self._session.execute(
            select(PasswordHistory.password_hash)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(limit),
        )
        return list(result.scalars().all())

    async def record_entry(self, *, user_id: int, password_hash: str) -> PasswordHistory:
        return await super().add(PasswordHistory(user_id=user_id, password_hash=password_hash))

    async def trim(self, user_id: int, *, keep: int) -> None:
        if keep <= 0:
            return
        result = await self._session.execute(
            select(PasswordHistory.id)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .offset(keep),
        )
        stale_ids = list(result.scalars().all())
        if not stale_ids:
            return
        await self._session.execute(
            delete(PasswordHistory).where(PasswordHistory.id.in_(stale_ids)),
        )

    async def password_reused(self, user_id: int, password: str, *, history_count: int) -> bool:
        if history_count <= 0:
            return False
        for password_hash in await self.list_recent_hashes(user_id, limit=history_count):
            if verify_password(password_hash, password):
                return True
        return False
