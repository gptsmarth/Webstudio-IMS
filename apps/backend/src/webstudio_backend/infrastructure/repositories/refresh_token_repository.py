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

    async def create(self, *, user_id: int, token_hash: str, expires_at: datetime) -> RefreshToken:
        return await self.add(
            RefreshToken(
                user_id=user_id,
                token_hash=token_hash,
                expires_at=expires_at,
            ),
        )

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
