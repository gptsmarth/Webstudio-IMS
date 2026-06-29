"""RefreshToken persistence repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.refresh_token import RefreshToken
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class RefreshTokenRepository(SqlAlchemyRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash),
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        token_hash: str,
        expires_at: datetime,
        ip_address: str | None = None,
        user_agent: str | None = None,
        device_label: str | None = None,
        remember_me: bool = False,
    ) -> RefreshToken:
        now = datetime.now(UTC)
        return await self.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
                ip_address=ip_address,
                user_agent=user_agent,
                device_label=device_label,
                last_used_at=now,
                remember_me=remember_me,
            ),
        )

    async def touch(self, token: RefreshToken) -> None:
        token.last_used_at = datetime.now(UTC)
        await self._session.flush()

    async def list_active_for_user(self, user_id: int) -> list[RefreshToken]:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .order_by(RefreshToken.last_used_at.desc().nullslast(), RefreshToken.created_at.desc()),
        )
        return list(result.scalars().all())

    async def get_active_for_user(self, user_id: int, session_id: int) -> RefreshToken | None:
        token = await self._session.get(RefreshToken, session_id)
        if token is None or token.user_id != user_id or token.revoked_at is not None:
            return None
        if token.expires_at <= datetime.now(UTC):
            return None
        return token

    async def count_active_by_user_ids(self, user_ids: list[int]) -> dict[int, int]:
        if not user_ids:
            return {}
        from sqlalchemy import func

        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshToken.user_id, func.count())
            .where(
                RefreshToken.user_id.in_(user_ids),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
            .group_by(RefreshToken.user_id),
        )
        return {int(user_id): int(count) for user_id, count in result.all()}

    async def revoke_by_id(self, session_id: int) -> None:
        token = await self._session.get(RefreshToken, session_id)
        if token is not None and token.revoked_at is None:
            await self.revoke(token)

    async def revoke(self, token: RefreshToken, *, replaced_by_id: int | None = None) -> None:
        token.revoked_at = datetime.now(UTC)
        if replaced_by_id is not None:
            token.replaced_by_id = replaced_by_id
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC)),
        )

    async def revoke_family(self, token: RefreshToken) -> None:
        await self.revoke_all_for_user(token.user_id)
