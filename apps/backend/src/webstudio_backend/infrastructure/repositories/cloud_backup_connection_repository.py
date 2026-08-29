"""Cloud backup connection persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.cloud_backup_connection import (
    CloudBackupConnection,
)
from webstudio_backend.infrastructure.database.repositories.base import SqlAlchemyRepository

GOOGLE_DRIVE_PROVIDER = "google_drive"


class CloudBackupConnectionRepository(SqlAlchemyRepository[CloudBackupConnection]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CloudBackupConnection)

    async def get_by_provider(self, provider: str) -> CloudBackupConnection | None:
        result = await self._session.execute(
            select(CloudBackupConnection).where(CloudBackupConnection.provider == provider),
        )
        return result.scalar_one_or_none()

    async def upsert_connected(
        self,
        *,
        provider: str,
        account_email: str,
        encrypted_refresh_token: str,
        drive_folder_id: str | None,
        connected_by_user_id: int | None,
    ) -> CloudBackupConnection:
        record = await self.get_by_provider(provider)
        now = datetime.now(UTC)
        if record is None:
            record = CloudBackupConnection(
                provider=provider,
                account_email=account_email,
                encrypted_refresh_token=encrypted_refresh_token,
                drive_folder_id=drive_folder_id,
                status="connected",
                connected_by_user_id=connected_by_user_id,
            )
            self._session.add(record)
        else:
            record.account_email = account_email
            record.encrypted_refresh_token = encrypted_refresh_token
            record.drive_folder_id = drive_folder_id
            record.status = "connected"
            record.connected_by_user_id = connected_by_user_id
            record.last_error = None
        record.connected_at = now
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def mark_disconnected(self, record: CloudBackupConnection) -> CloudBackupConnection:
        record.status = "disconnected"
        record.encrypted_refresh_token = ""
        record.drive_folder_id = None
        record.last_error = None
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def update_retention(
        self, record: CloudBackupConnection, *, retention_count: int
    ) -> CloudBackupConnection:
        record.retention_count = retention_count
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def record_sync_result(
        self,
        record: CloudBackupConnection,
        *,
        status: str,
        error: str | None,
    ) -> CloudBackupConnection:
        record.last_sync_at = datetime.now(UTC)
        record.last_sync_status = status
        record.last_error = error
        await self._session.flush()
        await self._session.refresh(record)
        return record

    async def set_status(
        self, record: CloudBackupConnection, *, status: str, error: str | None = None
    ) -> CloudBackupConnection:
        record.status = status
        if error is not None:
            record.last_error = error
        await self._session.flush()
        await self._session.refresh(record)
        return record
