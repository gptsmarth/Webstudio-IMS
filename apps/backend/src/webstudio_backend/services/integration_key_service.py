"""Encrypted integration API key management."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings, get_settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.integration_api_key import IntegrationApiKey
from webstudio_backend.infrastructure.repositories.integration_api_key_repository import (
    IntegrationApiKeyRepository,
)
from webstudio_backend.infrastructure.security.secret_encryption import encrypt_secret, mask_secret

ALLOWED_SERVICE_TYPES = frozenset({"email", "sms", "whatsapp", "custom"})


class IntegrationKeyNotFoundError(ValueError):
    def __init__(self, key_id: int) -> None:
        super().__init__(f"Integration key {key_id} not found")
        self.key_id = key_id


class IntegrationKeyService:
    def __init__(self, session: AsyncSession, app_settings: Settings | None = None) -> None:
        self._session = session
        self._settings = app_settings or get_settings()
        self._keys = IntegrationApiKeyRepository(session)
        self._recorder = AuditRecorder(session)

    async def list_keys(self, *, include_archived: bool = False) -> list[dict]:
        records = await self._keys.list_keys(include_archived=include_archived)
        return [self._serialize(record) for record in records]

    async def get_key(self, key_id: int) -> dict:
        record = await self._require_key(key_id)
        return self._serialize(record)

    async def create_key(
        self,
        *,
        service_type: str,
        label: str,
        api_key: str,
        actor: AuditActor,
    ) -> dict:
        normalized_type = self._normalize_service_type(service_type)
        trimmed_label = label.strip()
        trimmed_key = api_key.strip()
        if not trimmed_label:
            raise ValueError("Label is required")
        if not trimmed_key:
            raise ValueError("API key is required")
        encrypted = encrypt_secret(trimmed_key, secret=self._settings.jwt_secret)
        record = await self._keys.create(
            service_type=normalized_type,
            label=trimmed_label,
            encrypted_value=encrypted,
            key_hint=mask_secret(trimmed_key),
            created_by_user_id=actor.user_id,
        )
        await self._recorder.record_integration_key_create(
            key_id=record.id,
            service_type=record.service_type,
            label=record.label,
            actor=actor,
        )
        return self._serialize(record)

    async def update_key(
        self,
        key_id: int,
        *,
        label: str | None,
        api_key: str | None,
        actor: AuditActor,
    ) -> dict:
        record = await self._require_key(key_id)
        if label is not None:
            trimmed_label = label.strip()
            if not trimmed_label:
                raise ValueError("Label is required")
            record = await self._keys.update_label(
                record,
                label=trimmed_label,
                actor_id=actor.user_id,
            )
            await self._recorder.record_integration_key_update(
                key_id=record.id,
                service_type=record.service_type,
                label=record.label,
                actor=actor,
                field_name="label",
            )
        if api_key is not None:
            trimmed_key = api_key.strip()
            if not trimmed_key:
                raise ValueError("API key cannot be empty")
            encrypted = encrypt_secret(trimmed_key, secret=self._settings.jwt_secret)
            record = await self._keys.update_secret(
                record,
                encrypted_value=encrypted,
                key_hint=mask_secret(trimmed_key),
                actor_id=actor.user_id,
            )
            await self._recorder.record_integration_key_update(
                key_id=record.id,
                service_type=record.service_type,
                label=record.label,
                actor=actor,
                field_name="api_key",
            )
        return self._serialize(record)

    async def archive_key(self, key_id: int, *, actor: AuditActor) -> dict:
        record = await self._require_key(key_id)
        if record.archived_at is not None:
            raise ValueError("Integration key is already archived")
        updated = await self._keys.archive(record, actor_id=actor.user_id)
        await self._recorder.record_integration_key_archive(
            key_id=updated.id,
            service_type=updated.service_type,
            label=updated.label,
            actor=actor,
        )
        return self._serialize(updated)

    async def restore_key(self, key_id: int, *, actor: AuditActor) -> dict:
        record = await self._require_key(key_id)
        if record.archived_at is None:
            raise ValueError("Integration key is not archived")
        updated = await self._keys.restore(record, actor_id=actor.user_id)
        await self._recorder.record_integration_key_restore(
            key_id=updated.id,
            service_type=updated.service_type,
            label=updated.label,
            actor=actor,
        )
        return self._serialize(updated)

    async def _require_key(self, key_id: int) -> IntegrationApiKey:
        record = await self._keys.get_by_id(key_id)
        if record is None:
            raise IntegrationKeyNotFoundError(key_id)
        return record

    def _normalize_service_type(self, service_type: str) -> str:
        normalized = service_type.strip().lower()
        if normalized not in ALLOWED_SERVICE_TYPES:
            raise ValueError(f"Unsupported service type: {service_type}")
        return normalized

    def _serialize(self, record: IntegrationApiKey) -> dict:
        return {
            "id": record.id,
            "service_type": record.service_type,
            "label": record.label,
            "key_hint": record.key_hint,
            "is_active": record.is_active,
            "is_archived": record.archived_at is not None,
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
        }
