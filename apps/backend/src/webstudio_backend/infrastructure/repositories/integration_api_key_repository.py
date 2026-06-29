"""Integration API key persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.integration_api_key import IntegrationApiKey
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository


class IntegrationApiKeyRepository(SqlAlchemyRepository[IntegrationApiKey]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IntegrationApiKey)

    async def list_keys(self, *, include_archived: bool = False) -> list[IntegrationApiKey]:
        statement = select(IntegrationApiKey).order_by(IntegrationApiKey.service_type, IntegrationApiKey.label)
        if not include_archived:
            statement = statement.where(IntegrationApiKey.archived_at.is_(None))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def get_by_id(self, key_id: int) -> IntegrationApiKey | None:
        return await self._session.get(IntegrationApiKey, key_id)

    async def create(
        self,
        *,
        service_type: str,
        label: str,
        encrypted_value: str,
        key_hint: str | None,
        created_by_user_id: int | None,
    ) -> IntegrationApiKey:
        return await self.add(
            IntegrationApiKey(
                service_type=service_type,
                label=label,
                encrypted_value=encrypted_value,
                key_hint=key_hint,
                created_by_user_id=created_by_user_id,
                updated_by_user_id=created_by_user_id,
            ),
        )

    async def update_secret(
        self,
        record: IntegrationApiKey,
        *,
        encrypted_value: str,
        key_hint: str | None,
        actor_id: int | None,
    ) -> IntegrationApiKey:
        record.encrypted_value = encrypted_value
        record.key_hint = key_hint
        record.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def update_label(
        self,
        record: IntegrationApiKey,
        *,
        label: str,
        actor_id: int | None,
    ) -> IntegrationApiKey:
        record.label = label
        record.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def archive(self, record: IntegrationApiKey, *, actor_id: int | None) -> IntegrationApiKey:
        record.archived_at = datetime.now(UTC)
        record.is_active = False
        record.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def restore(self, record: IntegrationApiKey, *, actor_id: int | None) -> IntegrationApiKey:
        record.archived_at = None
        record.is_active = True
        record.updated_by_user_id = actor_id
        await self._session.flush()
        await self._session.refresh(record)
        return record
