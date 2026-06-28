"""System information aggregation."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.services.backup_service import BackupService


class SystemInfoService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def build(self) -> dict:
        db_size = await self._database_size_bytes()
        disk = shutil.disk_usage("/")
        backups = BackupService().list_backups()
        last_backup = backups[0].created_at if backups else None

        tls_configured = bool(self._settings.tls_cert_path and self._settings.tls_key_path)
        logs_folder = os.environ.get("LOG_DIR", "logs")

        return {
            "app_version": self._settings.app_version,
            "api_version": self._settings.api_version,
            "environment": self._settings.app_env,
            "database_size_bytes": db_size,
            "storage_total_bytes": disk.total,
            "storage_used_bytes": disk.used,
            "storage_free_bytes": disk.free,
            "backup_folder": str(BackupService()._backup_dir),
            "last_backup_at": last_backup,
            "logs_folder": logs_folder,
            "jwt_access_token_ttl_minutes": self._settings.access_token_ttl_minutes,
            "jwt_refresh_token_ttl_days": self._settings.refresh_token_ttl_days,
            "jwt_issuer": self._settings.jwt_issuer,
            "jwt_audience": self._settings.jwt_audience,
            "https_configured": tls_configured,
            "https_certificate_status": "configured" if tls_configured else "not_configured",
        }

    async def _database_size_bytes(self) -> int:
        result = await self._session.execute(text("SELECT pg_database_size(current_database())"))
        value = result.scalar_one()
        return int(value or 0)
