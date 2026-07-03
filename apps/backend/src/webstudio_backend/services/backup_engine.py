"""Enterprise backup orchestration — full archives, verification, retention."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_completeness import (
    BACKUP_MANAGED_ASSET_DIRS,
    DATABASE_DUMP_MODE_DATA_ONLY,
    DATABASE_DUMP_MODE_FULL,
    count_local_asset_files,
    filter_alembic_version_copy_blocks,
    use_real_database_dump,
)
from webstudio_backend.services.backup_encryption import get_backup_encryption_provider
from webstudio_backend.services.backup_format import (
    FORMAT_LEGACY_SQL,
    LEGACY_SQL_PATTERN,
    detect_backup_format,
)
from webstudio_backend.services.backup_manifest import (
    build_manifest,
    compute_content_checksum,
    finalize_manifest,
)
from webstudio_backend.services.backup_storage import create_storage_backend

INCREMENTAL_NOT_IMPLEMENTED = (
    "Incremental backup is not yet implemented; a full backup was created instead."
)


@dataclass(frozen=True, slots=True)
class BackupResult:
    id: int
    filename: str
    path: str
    size_bytes: int
    created_at: str
    backup_type: str
    trigger_type: str
    verification_status: str
    duration_ms: int
    checksum_sha256: str
    warnings: list[str]
    errors: list[str]
    creator_display_name: str | None


class BackupEngine:
    def __init__(
        self,
        session: AsyncSession,
        app_settings: Settings,
        *,
        backup_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._settings = app_settings
        self._runs = BackupRunRepository(session)
        self._settings_repo = SystemSettingRepository(session)
        self._recorder = AuditRecorder(session)
        self._backup_root = backup_dir or self._resolve_backup_dir()

    async def create_backup(
        self,
        *,
        backup_type: str = "full",
        trigger_type: str = "manual",
        creator_user_id: int | None = None,
        creator_display_name: str | None = None,
        storage_backend: str = "local",
    ) -> BackupResult:
        started = time.perf_counter()
        warnings: list[str] = []
        errors: list[str] = []
        base_backup_id: int | None = None

        if backup_type == "incremental":
            warnings.append(INCREMENTAL_NOT_IMPLEMENTED)
            recent = await self._runs.list_recent(limit=1)
            if recent:
                base_backup_id = recent[0].id
            backup_type = "full"

        storage = create_storage_backend(storage_backend, self._backup_root)
        storage.ensure_ready()

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        filename = f"webstudio-backup-{stamp}.tar.gz"
        archive_path = storage.resolve_path(filename)

        run = await self._runs.create_run(
            filename=filename,
            archive_path=str(archive_path),
            backup_type=backup_type,
            trigger_type=trigger_type,
            storage_backend=storage_backend,
            creator_user_id=creator_user_id,
            creator_display_name=creator_display_name,
            base_backup_id=base_backup_id,
        )

        schema_version = await self._schema_version()
        encryption = get_backup_encryption_provider()
        manifest = await build_manifest(
            settings_repo=self._settings_repo,
            session=self._session,
            backup_type=backup_type,
            trigger_type=trigger_type,
            creator_display_name=creator_display_name,
            schema_version=schema_version,
            app_version=self._settings.app_version,
            api_version=self._settings.api_version,
            storage_backend=storage_backend,
            base_backup_id=base_backup_id,
            backup_run_id=run.id,
            encrypted=encryption.is_enabled(),
            database_dump_mode=DATABASE_DUMP_MODE_DATA_ONLY,
            managed_asset_file_count=0,
        )
        if encryption.is_enabled():
            manifest["encryption_algorithm"] = encryption.algorithm()

        try:
            with tempfile.TemporaryDirectory(prefix="webstudio-backup-") as temp_dir:
                workspace = Path(temp_dir)
                db_path = workspace / "database.sql"
                await asyncio.to_thread(self._dump_database, db_path)

                assets_dir = workspace / "assets"
                assets_dir.mkdir()
                managed_asset_file_count = self._copy_managed_assets(
                    assets_dir,
                    company_logo=await self._settings_repo.get_string("company_logo"),
                )
                manifest["managed_asset_file_count"] = managed_asset_file_count

                config_dir = workspace / "config"
                config_dir.mkdir()
                self._write_application_config(config_dir / "application.env.snapshot")
                settings_snapshot = await self._export_settings_snapshot()
                settings_bytes = json.dumps(settings_snapshot, indent=2).encode("utf-8")
                (config_dir / "settings-registry.json").write_bytes(settings_bytes)
                asset_manifest = self._build_asset_manifest(assets_dir)
                asset_manifest_bytes = json.dumps(asset_manifest, indent=2).encode("utf-8")
                (config_dir / "asset-manifest.json").write_bytes(asset_manifest_bytes)

                content_checksum = compute_content_checksum(
                    ("database.sql", db_path.read_bytes()),
                    ("config/settings-registry.json", settings_bytes),
                    ("config/asset-manifest.json", asset_manifest_bytes),
                )

                with tarfile.open(archive_path, "w:gz") as archive:
                    archive.add(db_path, arcname="database.sql")
                    if assets_dir.exists():
                        archive.add(assets_dir, arcname="assets")
                    if config_dir.exists():
                        archive.add(config_dir, arcname="config")

            stat = archive_path.stat()
            duration_ms = int((time.perf_counter() - started) * 1000)
            manifest = finalize_manifest(
                manifest,
                backup_size_bytes=stat.st_size,
                content_checksum=content_checksum,
                duration_ms=duration_ms,
            )
            self._patch_manifest_in_archive(archive_path, manifest)

            if encryption.is_enabled():
                encryption.encrypt_archive(archive_path)

            verification_status, verify_warnings, verify_errors = self._verify_archive(
                archive_path,
                manifest,
            )
            warnings.extend(verify_warnings)
            errors.extend(verify_errors)

            checksum = self._checksum_file(archive_path)
            stat = archive_path.stat()

            completed = await self._runs.mark_completed(
                run,
                size_bytes=stat.st_size,
                duration_ms=duration_ms,
                checksum_sha256=checksum,
                schema_version=schema_version,
                app_version=self._settings.app_version,
                verification_status=verification_status,
                warnings=warnings,
                errors=errors,
                manifest=manifest,
            )

            completed_at_value = (
                completed.completed_at.isoformat()
                if completed.completed_at
                else datetime.now(UTC).isoformat()
            )
            await self._settings_repo.set_value(
                "last_backup_at",
                completed_at_value,
                value_type=SettingValueType.STRING,
                updated_by_user_id=creator_user_id,
            )
            await self._apply_retention()
            await self._audit_backup(
                actor_id=creator_user_id,
                actor_name=creator_display_name,
                filename=filename,
                backup_type=backup_type,
                trigger_type=trigger_type,
                verification_status=verification_status,
                size_bytes=stat.st_size,
                success=not errors,
            )
            from webstudio_backend.services.backup_alert_service import BackupAlertService

            alerts = BackupAlertService(self._session)
            if errors:
                await alerts.notify_backup_failed(
                    filename=filename,
                    detail="; ".join(errors) or "Unknown error",
                )
            else:
                await alerts.notify_backup_completed(
                    filename=filename,
                    verification_status=verification_status,
                    size_bytes=stat.st_size,
                )
            await alerts.maybe_notify_low_storage(
                storage_free_bytes=shutil.disk_usage(self._backup_root.anchor or "/").free,
            )
            await self._session.commit()

            return BackupResult(
                id=completed.id,
                filename=completed.filename,
                path=completed.archive_path,
                size_bytes=completed.size_bytes,
                created_at=completed.created_at.isoformat(),
                backup_type=completed.backup_type,
                trigger_type=completed.trigger_type,
                verification_status=completed.verification_status,
                duration_ms=duration_ms,
                checksum_sha256=checksum,
                warnings=warnings,
                errors=errors,
                creator_display_name=creator_display_name,
            )
        except Exception as exc:
            errors.append(str(exc))
            await self._runs.mark_failed(run, errors=errors)
            await self._audit_backup(
                actor_id=creator_user_id,
                actor_name=creator_display_name,
                filename=filename,
                backup_type=backup_type,
                trigger_type=trigger_type,
                verification_status="failed",
                size_bytes=0,
                success=False,
            )
            from webstudio_backend.services.backup_alert_service import BackupAlertService

            await BackupAlertService(self._session).notify_backup_failed(
                filename=filename,
                detail=str(exc),
            )
            await self._session.commit()
            raise RepositoryError(f"Backup failed: {exc}") from exc

    async def list_dashboard_entries(self, *, limit: int = 25) -> list[dict]:
        runs = await self._runs.list_recent(limit=limit)
        entries = [self._run_to_dict(run) for run in runs]
        if entries:
            return entries
        return [self._legacy_entry(path) for path in self._legacy_sql_files()[:limit]]

    def restore_backup(self, filename: str) -> None:
        archive_path = self._backup_root / filename
        if not archive_path.is_file():
            raise RepositoryError(f"Backup not found: {filename}")
        loader = detect_backup_format(archive_path)
        if loader.format_id == FORMAT_LEGACY_SQL:
            self._restore_sql_file(archive_path)
            return
        manifest = loader.read_manifest(archive_path)
        dump_mode = str(manifest.get("database_dump_mode") or DATABASE_DUMP_MODE_FULL)
        with tempfile.TemporaryDirectory(prefix="webstudio-restore-") as temp_dir:
            workspace = Path(temp_dir)
            inspection = loader.extract(archive_path, workspace)
            if inspection.corruption_detected or not inspection.integrity_valid:
                detail = "; ".join(inspection.errors) or "Archive integrity check failed."
                raise RepositoryError(detail)
            sql_path = workspace / "database.sql"
            if not sql_path.is_file():
                raise RepositoryError("Backup archive is missing database.sql")
            self._restore_sql_file(sql_path, dump_mode=dump_mode)
            self.restore_managed_assets_from_workspace(workspace)

    def _run_to_dict(self, run: Any) -> dict:
        return {
            "id": run.id,
            "filename": run.filename,
            "size_bytes": run.size_bytes,
            "created_at": run.created_at.isoformat(),
            "backup_type": run.backup_type,
            "trigger_type": run.trigger_type,
            "status": run.status,
            "verification_status": run.verification_status,
            "duration_ms": run.duration_ms,
            "checksum_sha256": run.checksum_sha256,
            "app_version": run.app_version,
            "schema_version": run.schema_version,
            "warnings": json.loads(run.warnings_json or "[]"),
            "errors": json.loads(run.errors_json or "[]"),
            "creator_display_name": run.creator_display_name,
            "storage_backend": run.storage_backend,
            "is_archived": run.is_archived,
        }

    def _legacy_entry(self, path: Path) -> dict:
        stat = path.stat()
        return {
            "id": None,
            "filename": path.name,
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            "backup_type": "full",
            "trigger_type": "manual",
            "status": "completed",
            "verification_status": "unknown",
            "duration_ms": None,
            "checksum_sha256": None,
            "app_version": None,
            "schema_version": None,
            "warnings": [],
            "errors": [],
            "creator_display_name": None,
            "storage_backend": "local",
            "is_archived": False,
        }

    def _legacy_sql_files(self) -> list[Path]:
        if not self._backup_root.exists():
            return []
        return sorted(
            [
                path
                for path in self._backup_root.glob("*.sql")
                if LEGACY_SQL_PATTERN.match(path.name)
            ],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )

    async def _schema_version(self) -> str:
        try:
            result = await self._session.execute(
                text("SELECT version_num FROM webstudio.alembic_version"),
            )
            value = result.scalar_one_or_none()
            return str(value or "unknown")
        except Exception:
            return "unknown"

    async def _export_settings_snapshot(self) -> dict[str, str]:
        from webstudio_backend.services.settings_registry import SETTING_DEFAULTS

        snapshot: dict[str, str] = {}
        for key in SETTING_DEFAULTS:
            if key in {"gemini_api_key"}:
                snapshot[key] = "[encrypted]"
                continue
            value = await self._settings_repo.get_string(key)
            snapshot[key] = value or ""
        return snapshot

    def _postgres_connection(self) -> tuple[str, str, str, str, str]:
        """Return pg_dump/psql connection params derived from DATABASE_URL."""
        parsed = urlparse(self._settings.database_url.replace("+asyncpg", ""))
        user = parsed.username or os.environ.get("POSTGRES_USER", "webstudio_app")
        password = parsed.password or os.environ.get("POSTGRES_PASSWORD", "")
        host = parsed.hostname or "127.0.0.1"
        if host in {"localhost", "::1"}:
            # Force TCP so pg_dump hits Docker-mapped Postgres instead of a local socket.
            host = "127.0.0.1"
        port = str(parsed.port or 5432)
        db_name = (parsed.path or "/webstudio_dev").lstrip("/") or "webstudio_dev"
        return user, password, host, port, db_name

    def _dump_database(self, output_path: Path) -> None:
        if self._settings.is_test and not use_real_database_dump():
            output_path.write_text("-- WEBSTUDIO IMS test backup\nSELECT 1;\n", encoding="utf-8")
            return

        docker_root = self._find_compose_root()
        dump_args = [
            "--schema",
            DATABASE_SCHEMA,
            "--data-only",
            "--no-owner",
            "--no-privileges",
            f"--exclude-table-data={DATABASE_SCHEMA}.alembic_version",
        ]
        user, _password, _host, _port, db_name = self._postgres_connection()
        if docker_root is not None:
            cmd = [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                user,
                *dump_args,
                db_name,
            ]
            try:
                with output_path.open("w", encoding="utf-8") as handle:
                    subprocess.run(
                        cmd,
                        check=True,
                        stdout=handle,
                        cwd=docker_root,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                return
            except (OSError, subprocess.CalledProcessError):
                pass

        try:
            self._dump_database_direct(output_path, extra_args=dump_args)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or str(exc)).strip()
            user, _password, host, port, db_name = self._postgres_connection()
            raise RepositoryError(
                "Database dump failed. Ensure PostgreSQL is running "
                f"(try: docker compose up -d postgres) and DATABASE_URL is correct. "
                f"Attempted {user}@{host}:{port}/{db_name}. {detail}"
            ) from exc

    def _dump_database_direct(
        self,
        output_path: Path,
        *,
        extra_args: list[str] | None = None,
    ) -> None:
        user, password, host, port, db_name = self._postgres_connection()
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        cmd = ["pg_dump", "-h", host, "-p", port, "-U", user, *(extra_args or []), db_name]
        with output_path.open("w", encoding="utf-8") as handle:
            subprocess.run(
                cmd, check=True, stdout=handle, env=env, stderr=subprocess.PIPE, text=True
            )

    def _restore_sql_file(self, path: Path, *, dump_mode: str = DATABASE_DUMP_MODE_FULL) -> None:
        if self._settings.is_test and not use_real_database_dump():
            return
        if dump_mode == DATABASE_DUMP_MODE_DATA_ONLY:
            self._restore_data_only_sql_file(path)
            return
        self._psql_restore_from_file(path, on_error_stop=False)

    def _restore_data_only_sql_file(self, path: Path) -> None:
        sql = filter_alembic_version_copy_blocks(path.read_text(encoding="utf-8"))
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".sql",
            delete=False,
        ) as handle:
            handle.write(sql)
            filtered_path = Path(handle.name)
        try:
            self._psql_restore_from_file(filtered_path, on_error_stop=True)
        finally:
            filtered_path.unlink(missing_ok=True)

    def _psql_restore_from_file(self, path: Path, *, on_error_stop: bool) -> None:
        user, password, host, port, db_name = self._postgres_connection()
        docker_root = self._find_compose_root()
        if docker_root is not None:
            cmd = ["docker", "compose", "exec", "-T", "postgres", "psql"]
            if on_error_stop:
                cmd.extend(["-v", "ON_ERROR_STOP=1"])
            cmd.extend(["-U", user, db_name])
            try:
                with path.open("r", encoding="utf-8") as handle:
                    subprocess.run(
                        cmd,
                        check=True,
                        stdin=handle,
                        cwd=docker_root,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                return
            except (OSError, subprocess.CalledProcessError):
                pass

        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        cmd = ["psql", "-h", host, "-p", port, "-U", user]
        if on_error_stop:
            cmd.extend(["-v", "ON_ERROR_STOP=1"])
        cmd.append(db_name)
        try:
            with path.open("r", encoding="utf-8") as handle:
                subprocess.run(
                    cmd, check=True, stdin=handle, env=env, stderr=subprocess.PIPE, text=True
                )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or str(exc)).strip()
            raise RepositoryError(
                "Restore failed. Check database connectivity. "
                f"Attempted {user}@{host}:{port}/{db_name}. {detail}",
            ) from exc

    def _copy_managed_assets(self, assets_dir: Path, *, company_logo: str | None) -> int:
        self._copy_brand_logos(assets_dir / "brand-logos")
        self._copy_company_logo_sync(assets_dir / "company", company_logo)
        public_assets = self._find_public_assets_dir()
        if public_assets is not None:
            for subdir in BACKUP_MANAGED_ASSET_DIRS:
                if subdir in {"brand-logos", "company"}:
                    continue
                source = public_assets / subdir
                if source.is_dir():
                    self._copy_directory_files(source, assets_dir / subdir)
        return count_local_asset_files(assets_dir)

    def _copy_directory_files(self, source: Path, target: Path) -> None:
        if not source.is_dir():
            return
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                shutil.copy2(item, target / item.name)

    def _copy_company_logo_sync(self, target: Path, company_logo: str | None) -> None:
        if not company_logo or not company_logo.strip():
            return
        logo = company_logo.strip()
        candidates: list[Path] = []
        path = Path(logo)
        if path.is_file():
            candidates.append(path)
        repo = self._find_repo_root()
        if repo is not None:
            candidates.append(repo / "apps/desktop/public" / logo.lstrip("/"))
        for candidate in candidates:
            if candidate.is_file():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, target / candidate.name)
                return

    def _build_asset_manifest(self, assets_dir: Path) -> dict[str, Any]:
        manifest: dict[str, Any] = {"directories": {}, "total_files": 0}
        if not assets_dir.is_dir():
            return manifest
        for subdir in BACKUP_MANAGED_ASSET_DIRS:
            folder = assets_dir / subdir
            if not folder.is_dir():
                continue
            files = sorted(
                item.name for item in folder.iterdir() if item.is_file() and item.name != ".gitkeep"
            )
            manifest["directories"][subdir] = files
            manifest["total_files"] += len(files)
        return manifest

    def restore_managed_assets_from_workspace(self, workspace: Path) -> None:
        assets_root = workspace / "assets"
        if not assets_root.is_dir():
            return
        public_assets = self._find_public_assets_dir()
        if public_assets is None:
            return
        for subdir in BACKUP_MANAGED_ASSET_DIRS:
            source = assets_root / subdir
            if not source.is_dir():
                continue
            self._copy_directory_files(source, public_assets / subdir)

    def _copy_brand_logos(self, target: Path) -> None:
        source = self._find_brand_logos_dir()
        if source is None or not source.is_dir():
            return
        target.mkdir(parents=True, exist_ok=True)
        for item in source.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                shutil.copy2(item, target / item.name)

    async def _copy_company_logo(self, target: Path, company_logo: str | None) -> None:
        if not company_logo or not company_logo.strip():
            return
        logo = company_logo.strip()
        candidates: list[Path] = []
        path = Path(logo)
        if path.is_file():
            candidates.append(path)
        repo = self._find_repo_root()
        if repo is not None:
            candidates.append(repo / "apps/desktop/public" / logo.lstrip("/"))
        for candidate in candidates:
            if candidate.is_file():
                target.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, target / candidate.name)
                return

    def _write_application_config(self, target: Path) -> None:
        lines = [
            f"APP_ENV={self._settings.app_env}",
            f"APP_VERSION={self._settings.app_version}",
            f"API_VERSION={self._settings.api_version}",
            "JWT_SECRET=[redacted]",
            "DATABASE_URL=[redacted]",
        ]
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _verify_archive(
        self,
        archive_path: Path,
        manifest: dict[str, Any],
    ) -> tuple[str, list[str], list[str]]:
        warnings: list[str] = []
        errors: list[str] = []
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                names = archive.getnames()
                for required in ("manifest.json", "database.sql"):
                    if required not in names:
                        errors.append(f"Missing required archive member: {required}")
                db_info = archive.getmember("database.sql")
                if db_info.size < 16:
                    warnings.append("Database dump appears unusually small.")
        except tarfile.TarError as exc:
            errors.append(f"Archive integrity check failed: {exc}")
            return "failed", warnings, errors

        if manifest.get("checksum_algorithm") != "sha256":
            warnings.append("Unexpected checksum algorithm in manifest.")
        from webstudio_backend.services.backup_manifest import validate_manifest_structure

        manifest_warnings, manifest_errors = validate_manifest_structure(manifest)
        warnings.extend(manifest_warnings)
        errors.extend(manifest_errors)
        if errors:
            return "failed", warnings, errors
        if warnings:
            return "warning", warnings, errors
        return "success", warnings, errors

    def _patch_manifest_in_archive(self, archive_path: Path, manifest: dict[str, Any]) -> None:
        with tempfile.TemporaryDirectory(prefix="webstudio-manifest-patch-") as temp_dir:
            workspace = Path(temp_dir)
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(workspace, filter="data")
            (workspace / "manifest.json").write_text(
                json.dumps(manifest, indent=2),
                encoding="utf-8",
            )
            with tarfile.open(archive_path, "w:gz") as archive:
                for path in sorted(workspace.rglob("*")):
                    if path.is_file():
                        archive.add(path, arcname=path.relative_to(workspace).as_posix())

    def read_manifest_from_archive(self, archive_path: Path) -> dict[str, Any]:
        try:
            return detect_backup_format(archive_path).read_manifest(archive_path)
        except (RepositoryError, OSError):
            return {}

    def _checksum_file(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    async def _apply_retention(self) -> None:
        policy = await self._settings_repo.get_string("backup_retention_policy") or "last_30"
        custom_count = await self._settings_repo.get_int("backup_retention_count", default=30)
        from webstudio_backend.services.backup_schedule import resolve_retention_limit

        retention = resolve_retention_limit(policy, custom_count)
        if retention is None:
            return
        runs = await self._runs.list_recent(limit=500, include_archived=False)
        for run in runs[retention:]:
            if run.is_archived:
                continue
            path = Path(run.archive_path)
            if path.is_file():
                path.unlink(missing_ok=True)
            await self._runs.delete_run(run)
        for path in self._legacy_sql_files()[retention:]:
            path.unlink(missing_ok=True)

    async def _audit_backup(
        self,
        *,
        actor_id: int | None,
        actor_name: str | None,
        filename: str,
        backup_type: str,
        trigger_type: str,
        verification_status: str,
        size_bytes: int,
        success: bool,
    ) -> None:
        actor = AuditActor(
            user_id=actor_id,
            display_name=actor_name or "System",
            role="main_admin" if actor_id else "system",
        )
        await self._recorder.record_backup_operation(
            filename=filename,
            backup_type=backup_type,
            trigger_type=trigger_type,
            verification_status=verification_status,
            size_bytes=size_bytes,
            actor=actor,
            success=success,
        )

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

    def _find_compose_root(self) -> Path | None:
        cwd = Path.cwd()
        for candidate in (cwd, cwd.parent, cwd.parent.parent):
            has_compose = (candidate / "docker-compose.yml").is_file()
            has_compose_yaml = (candidate / "compose.yaml").is_file()
            if has_compose or has_compose_yaml:
                return candidate
        return None

    def _find_repo_root(self) -> Path | None:
        cwd = Path.cwd()
        for candidate in (cwd, cwd.parent, cwd.parent.parent, cwd.parent.parent.parent):
            if (candidate / "apps" / "desktop").is_dir():
                return candidate
        return None

    def _find_brand_logos_dir(self) -> Path | None:
        public_assets = self._find_public_assets_dir()
        if public_assets is None:
            return None
        logos = public_assets / "brand-logos"
        return logos if logos.is_dir() else None

    def _find_public_assets_dir(self) -> Path | None:
        repo = self._find_repo_root()
        if repo is None:
            return None
        assets = repo / "apps/desktop/public/assets"
        return assets if assets.is_dir() else None
