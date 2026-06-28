"""Database backup and restore operations."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError


BACKUP_NAME_PATTERN = re.compile(r"^webstudio-.+\.sql$")


@dataclass(frozen=True, slots=True)
class BackupEntry:
    filename: str
    path: str
    size_bytes: int
    created_at: str


class BackupService:
    def __init__(self, *, backup_dir: Path | None = None) -> None:
        self._backup_dir = backup_dir or self._resolve_backup_dir()

    def _resolve_backup_dir(self) -> Path:
        env_dir = os.environ.get("BACKUP_DIR", "").strip()
        if env_dir:
            return Path(env_dir).expanduser().resolve()
        # repo root: apps/backend/src/... -> parents[4] may vary; walk up for backups/
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
        for path in sorted(self._backup_dir.glob("*.sql"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not BACKUP_NAME_PATTERN.match(path.name):
                continue
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

    def create_backup(self) -> BackupEntry:
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        db_name = os.environ.get("POSTGRES_DB", "webstudio_dev")
        filename = f"webstudio-{db_name}-{stamp}.sql"
        output = self._backup_dir / filename

        user = os.environ.get("POSTGRES_USER", "webstudio")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "pg_dump",
            "-U",
            user,
            db_name,
        ]
        try:
            with output.open("w", encoding="utf-8") as handle:
                subprocess.run(cmd, check=True, stdout=handle, cwd=self._find_compose_root())
        except (OSError, subprocess.CalledProcessError) as exc:
            if output.exists():
                output.unlink(missing_ok=True)
            raise RepositoryError(
                "Backup failed. Ensure PostgreSQL is running (docker compose up -d).",
            ) from exc

        stat = output.stat()
        return BackupEntry(
            filename=filename,
            path=str(output),
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        )

    def restore_backup(self, filename: str) -> None:
        if not BACKUP_NAME_PATTERN.match(filename):
            raise RepositoryError("Invalid backup filename")
        path = self._backup_dir / filename
        if not path.is_file():
            raise RepositoryError(f"Backup not found: {filename}")

        user = os.environ.get("POSTGRES_USER", "webstudio")
        db_name = os.environ.get("POSTGRES_DB", "webstudio_dev")
        cmd = [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            user,
            db_name,
        ]
        try:
            with path.open("r", encoding="utf-8") as handle:
                subprocess.run(cmd, check=True, stdin=handle, cwd=self._find_compose_root())
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RepositoryError("Restore failed. Check database connectivity and backup file.") from exc

    def _find_compose_root(self) -> Path:
        cwd = Path.cwd()
        for candidate in (cwd, cwd.parent, cwd.parent.parent):
            if (candidate / "docker-compose.yml").is_file() or (candidate / "compose.yaml").is_file():
                return candidate
        return cwd
