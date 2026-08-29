"""Google Drive connection management for cloud backup sync (Settings API)."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.models.cloud_backup_connection import (
    CloudBackupConnection,
)
from webstudio_backend.infrastructure.repositories.cloud_backup_connection_repository import (
    GOOGLE_DRIVE_PROVIDER,
    CloudBackupConnectionRepository,
)
from webstudio_backend.infrastructure.security.secret_encryption import encrypt_secret
from webstudio_backend.services.google_drive_client import GoogleDriveClient


class CloudBackupConnectionService:
    def __init__(self, session: AsyncSession, app_settings: Settings) -> None:
        self._session = session
        self._settings = app_settings
        self._connections = CloudBackupConnectionRepository(session)
        self._recorder = AuditRecorder(session)

    async def get_status(self) -> dict:
        record = await self._connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
        if record is None:
            return {
                "provider": GOOGLE_DRIVE_PROVIDER,
                "connected": False,
                "account_email": None,
                "status": "disconnected",
                "last_sync_at": None,
                "last_sync_status": None,
                "last_error": None,
                "retention_count": 25,
            }
        return self._serialize(record)

    async def connect(
        self,
        *,
        refresh_token: str,
        account_email: str,
        actor: AuditActor,
    ) -> dict:
        client = GoogleDriveClient(
            refresh_token=refresh_token,
            client_id=self._settings.google_drive_client_id,
            client_secret=self._settings.google_drive_client_secret,
        )
        folder_id = await asyncio.to_thread(client.ensure_backup_folder)

        encrypted = encrypt_secret(refresh_token, secret=self._settings.jwt_secret)
        record = await self._connections.upsert_connected(
            provider=GOOGLE_DRIVE_PROVIDER,
            account_email=account_email.strip(),
            encrypted_refresh_token=encrypted,
            drive_folder_id=folder_id,
            connected_by_user_id=actor.user_id,
        )
        await self._recorder.record_configuration_change(
            setting_key="cloud_backup_google_drive_connect",
            category="backup",
            old_value=None,
            new_value=account_email.strip(),
            actor=actor,
        )
        return self._serialize(record)

    async def disconnect(self, *, actor: AuditActor) -> dict:
        record = await self._connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
        if record is None:
            raise ValueError("Google Drive is not connected")
        previous_email = record.account_email
        updated = await self._connections.mark_disconnected(record)
        await self._recorder.record_configuration_change(
            setting_key="cloud_backup_google_drive_disconnect",
            category="backup",
            old_value=previous_email,
            new_value=None,
            actor=actor,
        )
        return self._serialize(updated)

    async def update_retention(self, *, retention_count: int, actor: AuditActor) -> dict:
        record = await self._connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
        if record is None:
            raise ValueError("Google Drive is not connected")
        previous = record.retention_count
        updated = await self._connections.update_retention(record, retention_count=retention_count)
        await self._recorder.record_configuration_change(
            setting_key="cloud_backup_retention_count",
            category="backup",
            old_value=str(previous),
            new_value=str(retention_count),
            actor=actor,
        )
        return self._serialize(updated)

    def _serialize(self, record: CloudBackupConnection) -> dict:
        return {
            "provider": record.provider,
            "connected": record.status == "connected",
            "account_email": record.account_email,
            "status": record.status,
            "last_sync_at": record.last_sync_at.isoformat() if record.last_sync_at else None,
            "last_sync_status": record.last_sync_status,
            "last_error": record.last_error,
            "retention_count": record.retention_count,
        }
