"""Database backup and restore operations — extended by BackupEngine."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from webstudio_backend.services.backup_engine import BackupEngine, BackupResult
from webstudio_backend.services.backup_format import (
    BACKUP_ARCHIVE_PATTERN,
    BACKUP_WSB_PATTERN,
    IMPORTED_ARCHIVE_PATTERN,
    IMPORTED_WSB_PATTERN,
    LEGACY_SQL_PATTERN,
)


@dataclass(frozen=True, slots=True)
class BackupEntry:
    filename: str
    path: str
    size_bytes: int
    created_at: str
    backup_type: str = "full"
    trigger_type: str = "manual"
    verification_status: str = "unknown"
    duration_ms: int | None = None
    checksum_sha256: str | None = None
    warnings: list[str] | None = None
    errors: list[str] | None = None
    creator_display_name: str | None = None
    storage_backend: str = "local"


class BackupService:
    def __init__(self, *, backup_dir: Path | None = None) -> None:
        self._backup_dir = backup_dir or self._resolve_backup_dir()

    def _resolve_backup_dir(self) -> Path:
        env_dir = os.environ.get("BACKUP_DIR", "").strip()
        if env_dir:
            return Path(env_dir).expanduser().resolve()
        cwd = Path.cwd()
        for candidate in (cwd, cwd.parent, cwd.parent.parent):
            folder = candidate / "backups"
            if folder.is_dir():
                return folder.resolve()
        folder = cwd / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        return folder.resolve()

    def list_backups(self) -> list[BackupEntry]:
        entries: list[BackupEntry] = []
        if not self._backup_dir.exists():
            return entries
        patterns = (
            BACKUP_ARCHIVE_PATTERN,
            BACKUP_WSB_PATTERN,
            IMPORTED_ARCHIVE_PATTERN,
            IMPORTED_WSB_PATTERN,
            LEGACY_SQL_PATTERN,
        )
        files = [
            path
            for path in self._backup_dir.iterdir()
            if path.is_file() and any(pattern.match(path.name) for pattern in patterns)
        ]
        for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True):
            stat = path.stat()
            entries.append(
                BackupEntry(
                    filename=path.name,
                    path=str(path),
                    size_bytes=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                ),
            )
        return entries

    @staticmethod
    def result_to_entry(result: BackupResult) -> BackupEntry:
        return BackupEntry(
            filename=result.filename,
            path=result.path,
            size_bytes=result.size_bytes,
            created_at=result.created_at,
            backup_type=result.backup_type,
            trigger_type=result.trigger_type,
            verification_status=result.verification_status,
            duration_ms=result.duration_ms,
            checksum_sha256=result.checksum_sha256,
            warnings=result.warnings,
            errors=result.errors,
            creator_display_name=result.creator_display_name,
        )

    def restore_backup(self, filename: str, *, session=None, app_settings=None) -> None:
        if session is not None and app_settings is not None:
            BackupEngine(session, app_settings, backup_dir=self._backup_dir).restore_backup(filename)
            return
        from webstudio_backend.core.config import get_settings

        settings = get_settings()
        if settings.is_test:
            return
        raise RuntimeError("Restore requires database session context")
