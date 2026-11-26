"""Enterprise backup orchestration — full archives, verification, retention."""

from __future__ import annotations

import asyncio
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
from urllib.parse import unquote, urlparse

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
from webstudio_backend.services.backup_assets import (
    asset_file_checksum,
    managed_backup_files,
    restore_managed_files,
)
from webstudio_backend.services.backup_completeness import (
    BACKUP_MANAGED_ASSET_DIRS,
    DATA_ONLY_RESTORE_FINISH,
    DATA_ONLY_RESTORE_START,
    DATABASE_DUMP_MODE_DATA_ONLY,
    SNAPSHOT_COUNT_TABLES,
    dump_snapshot_counts,
    prepare_data_only_restore_sql,
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
from webstudio_backend.services.postgres_cli import resolve_postgres_tool

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

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
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
                snapshot_counts = dump_snapshot_counts(db_path)
                if snapshot_counts:
                    manifest.update(snapshot_counts)
                    manifest["database_snapshot_counts"] = True

                assets_dir = workspace / "assets"
                assets_dir.mkdir()
                managed_asset_file_count = self._copy_managed_assets(assets_dir)
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

            verification_status, verify_warnings, verify_errors = self._verify_archive(archive_path)
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
            if trigger_type != "emergency":
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

    def restore_backup(self, filename: str) -> tuple[int, dict[str, Any]]:
        archive_path = self._backup_root / filename
        if (
            any(char in filename for char in "/\\:")
            or archive_path.is_symlink()
            or not archive_path.is_file()
        ):
            raise RepositoryError(f"Backup not found: {filename}")
        loader = detect_backup_format(archive_path)
        if loader.format_id == FORMAT_LEGACY_SQL:
            raise RepositoryError("Restore Center requires an IMS data-only archive.")
        with tempfile.TemporaryDirectory(prefix="webstudio-restore-") as temp_dir:
            workspace = Path(temp_dir)
            inspection = loader.extract(archive_path, workspace)
            if inspection.corruption_detected or not inspection.integrity_valid:
                detail = "; ".join(inspection.errors) or "Archive integrity check failed."
                raise RepositoryError(detail)
            manifest = inspection.manifest
            if manifest.get("database_dump_mode") != DATABASE_DUMP_MODE_DATA_ONLY:
                raise RepositoryError("Restore Center requires an IMS data-only archive.")
            schema = manifest.get("schema_version")
            if not isinstance(schema, str) or schema in {"", "unknown"}:
                raise RepositoryError("The backup does not identify its database revision.")
            sql_path = workspace / "database.sql"
            # Validate and prepare SQL before changing any managed files.
            sql = None
            if not self._settings.is_test or use_real_database_dump():
                sql = prepare_data_only_restore_sql(sql_path.read_text(encoding="utf-8"))
            expected_counts = {}
            if manifest.get("database_snapshot_counts"):
                for field, table in SNAPSHOT_COUNT_TABLES.items():
                    count = manifest.get(field)
                    if type(count) is not int or count < 0:
                        raise RepositoryError("The backup has invalid database record counts.")
                    expected_counts[table] = count
            with restore_managed_files(
                workspace / "assets",
                self._find_public_assets_dir(),
                expected_count=manifest.get("managed_asset_file_count"),
            ) as restored_count:
                if sql is not None:
                    self._restore_prepared_sql(sql, schema=schema, expected_counts=expected_counts)
                return restored_count, manifest

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
            "cloud_upload_status": run.cloud_upload_status,
            "cloud_uploaded_at": (
                run.cloud_uploaded_at.isoformat() if run.cloud_uploaded_at else None
            ),
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
            "cloud_upload_status": None,
            "cloud_uploaded_at": None,
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
        user = (
            unquote(parsed.username)
            if parsed.username
            else os.environ.get("POSTGRES_USER", "webstudio_app")
        )
        password = (
            unquote(parsed.password)
            if parsed.password is not None
            else os.environ.get("POSTGRES_PASSWORD", "")
        )
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 5432)
        db_name = (parsed.path or "/webstudio_dev").lstrip("/") or "webstudio_dev"
        return user, password, host, port, db_name

    def _dump_database(self, output_path: Path) -> None:
        if self._settings.is_test and not use_real_database_dump():
            output_path.write_text("-- WEBSTUDIO IMS test backup\nSELECT 1;\n", encoding="utf-8")
            return

        dump_args = [
            "--schema",
            DATABASE_SCHEMA,
            "--data-only",
            "--no-owner",
            "--no-privileges",
            # Preserve compatibility with previous IMS releases and their administrator
            # recovery procedure. The current restore handles FK checks transactionally.
            "--disable-triggers",
            f"--exclude-table-data={DATABASE_SCHEMA}.alembic_version",
            f"--exclude-table-data={DATABASE_SCHEMA}.laptop_comparison_cache",
            f"--exclude-table-data={DATABASE_SCHEMA}.asus_activation_workbooks",
        ]
        user, _password, _host, _port, db_name = self._postgres_connection()
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
        pg_dump = resolve_postgres_tool("pg_dump", postgres_bin=self._settings.postgres_bin)
        cmd = [pg_dump, "-h", host, "-p", port, "-U", user, *(extra_args or []), db_name]
        try:
            with output_path.open("w", encoding="utf-8") as handle:
                subprocess.run(
                    cmd, check=True, stdout=handle, env=env, stderr=subprocess.PIPE, text=True
                )
        except OSError as exc:
            raise RepositoryError(
                f"Could not run pg_dump at {pg_dump}. Set POSTGRES_BIN and restart the server."
            ) from exc

    def _restore_prepared_sql(
        self, sql: str, *, schema: str, expected_counts: dict[str, int] | None = None
    ) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".sql",
            delete=False,
        ) as handle:
            handle.write(
                "SELECT pg_catalog.set_config('webstudio.restore_revision', :'revision', true);\n"
            )
            handle.write(DATA_ONLY_RESTORE_START)
            handle.write(sql)
            handle.write(DATA_ONLY_RESTORE_FINISH)
            for table, count in (expected_counts or {}).items():
                handle.write(
                    f"DO $$ BEGIN IF (SELECT count(*) FROM webstudio.{table}) <> {count} "
                    f"THEN RAISE EXCEPTION 'Restore count does not match the backup for {table}'; "
                    "END IF; END $$;\n"
                )
            filtered_path = Path(handle.name)
        try:
            self._psql_restore_from_file(filtered_path, schema=schema)
        finally:
            filtered_path.unlink(missing_ok=True)

    def _psql_restore_from_file(self, path: Path, *, schema: str) -> None:
        user, password, host, port, db_name = self._postgres_connection()
        env = os.environ.copy()
        if password:
            env["PGPASSWORD"] = password
        psql = resolve_postgres_tool("psql", postgres_bin=self._settings.postgres_bin)
        cmd = [
            psql,
            "-X",
            "--no-password",
            "-h",
            host,
            "-p",
            port,
            "-U",
            user,
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            f"revision={schema}",
            "--single-transaction",
            "-f",
            "-",
            db_name,
        ]
        try:
            with path.open("r", encoding="utf-8") as handle:
                subprocess.run(
                    cmd,
                    check=True,
                    stdin=handle,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except OSError as exc:
            raise RepositoryError(
                f"Could not run psql at {psql}. Set POSTGRES_BIN and restart the server."
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = next(
                (line.strip() for line in (exc.stderr or "").splitlines() if line.strip()),
                f"psql exited with code {exc.returncode}.",
            )
            raise RepositoryError(
                "PostgreSQL could not load the backup. "
                f"Attempted {user}@{host}:{port}/{db_name}. {detail}",
            ) from exc

    def _copy_managed_assets(self, assets_dir: Path) -> int:
        from webstudio_backend.services.web_image_scraper import managed_asset_search_dirs

        for source in reversed(managed_asset_search_dirs(settings=self._settings)):
            for relative, item in managed_backup_files(source, BACKUP_MANAGED_ASSET_DIRS).items():
                target = assets_dir / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
        return len(managed_backup_files(assets_dir, BACKUP_MANAGED_ASSET_DIRS))

    def _build_asset_manifest(self, assets_dir: Path) -> dict[str, Any]:
        files = managed_backup_files(assets_dir, BACKUP_MANAGED_ASSET_DIRS)
        directories: dict[str, list[str]] = {}
        checksums: dict[str, str] = {}
        for relative, item in files.items():
            directory, *path = relative.parts
            directories.setdefault(directory, []).append("/".join(path))
            checksums[f"assets/{relative.as_posix()}"] = asset_file_checksum(item)
        return {"directories": directories, "total_files": len(files), "sha256": checksums}

    def _write_application_config(self, target: Path) -> None:
        lines = [
            f"APP_ENV={self._settings.app_env}",
            f"APP_VERSION={self._settings.app_version}",
            f"API_VERSION={self._settings.api_version}",
            "JWT_SECRET=[redacted]",
            "DATABASE_URL=[redacted]",
        ]
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _verify_archive(self, archive_path: Path) -> tuple[str, list[str], list[str]]:
        warnings: list[str] = []
        errors: list[str] = []
        try:
            inspection = detect_backup_format(archive_path).inspect(archive_path)
            errors.extend(inspection.errors)
            warnings.extend(inspection.warnings)
        except (RepositoryError, OSError) as exc:
            errors.append(f"Archive integrity check failed: {exc}")
            return "failed", warnings, errors

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
        return asset_file_checksum(path)

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

    def _find_public_assets_dir(self) -> Path | None:
        """Writable managed-assets root used by backups and restores.

        On office/production servers this is ``{WEBSTUDIO_DATA_ROOT}/assets``.
        Dev/test falls back to the repo public assets folder.
        """
        from webstudio_backend.services.web_image_scraper import resolve_managed_assets_dir

        return resolve_managed_assets_dir(create=False, settings=self._settings)
