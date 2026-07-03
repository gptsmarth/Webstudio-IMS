"""Enterprise restore orchestration — validation, emergency backup, rollback."""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
from webstudio_backend.infrastructure.repositories.restore_run_repository import (
    RestoreRunRepository,
    RestoreRunSnapshot,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_completeness import (
    DATABASE_DUMP_MODE_DATA_ONLY,
    truncate_webstudio_data,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.backup_format import (
    FORMAT_LEGACY_SQL,
    detect_backup_format,
    detect_import_extension,
    is_supported_backup_path,
)
from webstudio_backend.services.backup_manifest import (
    compatibility_report,
    manifest_preview_fields,
)
from webstudio_backend.services.backup_verification import verify_post_restore
from webstudio_backend.services.settings_registry import SETTING_DEFAULTS

RESTORE_SCOPES = frozenset(
    {
        "entire_database",
        "settings_only",
        "company_config",
        "users_only",
        "reports_only",
    }
)
IMPLEMENTED_SCOPES = frozenset({"entire_database", "settings_only", "company_config"})
COMPANY_CONFIG_KEYS = frozenset(
    {
        "company_name",
        "company_logo",
        "company_address",
        "gst_number",
        "company_phone",
        "company_email",
        "default_store_id",
        "default_language",
        "timezone",
        "currency",
    }
)
SETTINGS_EXCLUDED_KEYS = frozenset({"gemini_api_key", "system_initialized"})


@dataclass(frozen=True, slots=True)
class BackupValidationResult:
    valid: bool
    filename: str
    source: str
    checksum_valid: bool
    integrity_valid: bool
    corruption_detected: bool
    app_version: str | None
    schema_version: str | None
    backup_version: str | None
    current_app_version: str
    current_schema_version: str
    compatibility: str
    backup_type: str | None
    trigger_type: str | None
    timestamp: str | None
    size_bytes: int
    company_name: str | None
    created_by: str | None
    database_size_bytes: int | None
    inventory_count: int | None
    sales_count: int | None
    users_count: int | None
    audit_log_count: int | None
    restore_allowed: bool
    migration_required: bool
    compatibility_report: dict[str, Any]
    backup_format_id: str | None
    backup_format_label: str | None
    warnings: list[str]
    errors: list[str]


@dataclass(frozen=True, slots=True)
class RestorePreview:
    filename: str
    source: str
    restore_scope: str
    scope_implemented: bool
    backup_type: str | None
    trigger_type: str | None
    timestamp: str | None
    contents: list[str]
    affected_areas: list[str]
    warnings: list[str]
    emergency_backup_recommended: bool
    company_name: str | None
    created_by: str | None
    app_version: str | None
    backup_version: str | None
    schema_version: str | None
    inventory_count: int | None
    sales_count: int | None
    users_count: int | None
    database_size_bytes: int | None
    compressed_size_bytes: int
    checksum_valid: bool
    schema_compatibility: str
    restore_allowed: bool
    migration_required: bool
    compatibility_summary: str
    backup_format_id: str | None = None
    backup_format_label: str | None = None


@dataclass(frozen=True, slots=True)
class ImportBackupResult:
    filename: str
    backup_format_id: str
    backup_format_label: str


@dataclass(frozen=True, slots=True)
class RestoreResult:
    success: bool
    filename: str
    restore_scope: str
    emergency_backup_filename: str | None
    rollback_available: bool
    rollback_recommended: bool
    verification_status: str
    duration_ms: int
    warnings: list[str]
    errors: list[str]
    restart_required: bool
    verification_checks: list[dict[str, Any]]


class RestoreEngine:
    def __init__(
        self,
        session: AsyncSession,
        app_settings: Settings,
        *,
        backup_dir: Path | None = None,
    ) -> None:
        self._session = session
        self._settings = app_settings
        self._backup_engine = BackupEngine(session, app_settings, backup_dir=backup_dir)
        self._backup_root = self._backup_engine._backup_root  # noqa: SLF001
        self._runs = RestoreRunRepository(session)
        self._backup_runs = BackupRunRepository(session)
        self._settings_repo = SystemSettingRepository(session)
        self._recorder = AuditRecorder(session)

    async def validate_backup(
        self,
        filename: str,
        *,
        source: str = "local",
    ) -> BackupValidationResult:
        warnings: list[str] = []
        errors: list[str] = []
        archive_path = self._resolve_archive_path(filename)
        if not archive_path.is_file():
            raise RepositoryError(f"Backup not found: {filename}")

        current_schema = await self._backup_engine._schema_version()  # noqa: SLF001
        stat = archive_path.stat()
        loader = detect_backup_format(archive_path)
        inspection = loader.inspect(archive_path)
        warnings.extend(inspection.warnings)
        errors.extend(inspection.errors)

        if loader.format_id == FORMAT_LEGACY_SQL:
            compat = compatibility_report(
                {},
                current_app_version=self._settings.app_version,
                current_schema_version=current_schema,
                corruption_detected=inspection.corruption_detected,
                integrity_valid=inspection.integrity_valid,
            )
            return BackupValidationResult(
                valid=inspection.integrity_valid and not errors,
                filename=filename,
                source=source,
                checksum_valid=False,
                integrity_valid=inspection.integrity_valid,
                corruption_detected=inspection.corruption_detected,
                app_version=None,
                schema_version=None,
                backup_version=None,
                current_app_version=self._settings.app_version,
                current_schema_version=current_schema,
                compatibility="warning",
                backup_type="full",
                trigger_type="manual",
                timestamp=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
                size_bytes=stat.st_size,
                company_name=None,
                created_by=None,
                database_size_bytes=None,
                inventory_count=None,
                sales_count=None,
                users_count=None,
                audit_log_count=None,
                restore_allowed=compat["restore_allowed"],
                migration_required=compat["migration_required"],
                compatibility_report=compat,
                backup_format_id=loader.format_id,
                backup_format_label=loader.format_label,
                warnings=warnings,
                errors=errors,
            )

        manifest = inspection.manifest
        integrity_valid = inspection.integrity_valid
        corruption_detected = inspection.corruption_detected
        if corruption_detected:
            errors.append("Archive corruption detected.")
        if not integrity_valid and not errors:
            errors.append("Archive integrity check failed.")

        checksum_valid = await self._verify_checksum(filename, archive_path, manifest)
        if manifest and not checksum_valid:
            warnings.append("Checksum could not be verified against stored metadata.")

        app_version = str(manifest.get("app_version")) if manifest.get("app_version") else None
        raw_schema = manifest.get("schema_version")
        schema_version = str(raw_schema) if raw_schema else None
        raw_backup_version = manifest.get("backup_version")
        backup_version = str(raw_backup_version) if raw_backup_version else None
        compat = compatibility_report(
            manifest,
            current_app_version=self._settings.app_version,
            current_schema_version=current_schema,
            corruption_detected=corruption_detected,
            integrity_valid=integrity_valid,
        )
        compatibility = self._compatibility_status(app_version, schema_version, current_schema)

        if not compat["restore_allowed"]:
            errors.append(compat["summary"])
        elif compatibility == "warning" or compat["migration_required"]:
            warnings.append(compat["summary"])

        valid = not corruption_detected and integrity_valid and not errors
        return BackupValidationResult(
            valid=valid,
            filename=filename,
            source=source,
            checksum_valid=checksum_valid,
            integrity_valid=integrity_valid,
            corruption_detected=corruption_detected,
            app_version=app_version,
            schema_version=schema_version,
            backup_version=backup_version,
            current_app_version=self._settings.app_version,
            current_schema_version=current_schema,
            compatibility=compatibility,
            backup_type=str(manifest.get("backup_type")) if manifest else None,
            trigger_type=str(manifest.get("trigger_type")) if manifest else None,
            timestamp=str(manifest.get("timestamp")) if manifest else None,
            size_bytes=stat.st_size,
            company_name=(
                str(manifest.get("company_name")) if manifest.get("company_name") else None
            ),
            created_by=(
                str(manifest.get("created_by") or manifest.get("creator")) if manifest else None
            ),
            database_size_bytes=manifest.get("database_size_bytes"),
            inventory_count=manifest.get("inventory_count"),
            sales_count=manifest.get("sales_count"),
            users_count=manifest.get("users_count"),
            audit_log_count=manifest.get("audit_log_count"),
            restore_allowed=bool(compat["restore_allowed"]),
            migration_required=bool(compat["migration_required"]),
            compatibility_report=compat,
            backup_format_id=loader.format_id,
            backup_format_label=loader.format_label,
            warnings=warnings,
            errors=errors,
        )

    async def preview_restore(
        self,
        filename: str,
        *,
        restore_scope: str = "entire_database",
        source: str = "local",
    ) -> RestorePreview:
        if restore_scope not in RESTORE_SCOPES:
            raise RepositoryError(f"Unsupported restore scope: {restore_scope}")

        validation = await self.validate_backup(filename, source=source)
        manifest = await self._load_manifest(filename)
        manifest["filename"] = filename
        preview_fields = manifest_preview_fields(manifest, size_bytes=validation.size_bytes)
        contents = list(manifest.get("contents", [])) if manifest else ["postgresql_database"]
        scope_implemented = restore_scope in IMPLEMENTED_SCOPES
        warnings = list(validation.warnings)

        if restore_scope == "users_only":
            warnings.append("User-only restore requires full database restore (future-ready).")
        elif restore_scope == "reports_only":
            warnings.append("Report-only restore is not yet implemented (future-ready).")
        elif not scope_implemented:
            warnings.append(f"Restore scope '{restore_scope}' is not implemented.")

        return RestorePreview(
            filename=filename,
            source=source,
            restore_scope=restore_scope,
            scope_implemented=scope_implemented,
            backup_type=validation.backup_type,
            trigger_type=validation.trigger_type,
            timestamp=validation.timestamp,
            contents=contents,
            affected_areas=self._affected_areas(restore_scope),
            warnings=warnings,
            emergency_backup_recommended=restore_scope == "entire_database",
            company_name=preview_fields.get("company_name"),
            created_by=preview_fields.get("created_by"),
            app_version=preview_fields.get("app_version"),
            backup_version=preview_fields.get("backup_version"),
            schema_version=preview_fields.get("schema_version"),
            inventory_count=preview_fields.get("inventory_count"),
            sales_count=preview_fields.get("sales_count"),
            users_count=preview_fields.get("users_count"),
            database_size_bytes=preview_fields.get("database_size_bytes"),
            compressed_size_bytes=int(
                preview_fields.get("compressed_size_bytes") or validation.size_bytes,
            ),
            checksum_valid=validation.checksum_valid,
            schema_compatibility=validation.compatibility,
            restore_allowed=validation.restore_allowed,
            migration_required=validation.migration_required,
            compatibility_summary=str(validation.compatibility_report.get("summary", "")),
            backup_format_id=validation.backup_format_id,
            backup_format_label=validation.backup_format_label,
        )

    async def execute_restore(
        self,
        *,
        filename: str,
        restore_scope: str = "entire_database",
        source: str = "local",
        create_emergency_backup: bool | None = None,
        confirmed: bool = False,
        actor_user_id: int | None = None,
        actor_display_name: str | None = None,
        rollback: bool = False,
    ) -> RestoreResult:
        if not confirmed:
            raise RepositoryError("Restore requires explicit confirmation.")
        if restore_scope not in RESTORE_SCOPES:
            raise RepositoryError(f"Unsupported restore scope: {restore_scope}")
        if restore_scope not in IMPLEMENTED_SCOPES:
            raise RepositoryError(f"Restore scope '{restore_scope}' is not yet implemented.")

        started = time.perf_counter()
        warnings: list[str] = []
        errors: list[str] = []
        emergency_filename: str | None = None

        validation = await self.validate_backup(filename, source=source)
        warnings.extend(validation.warnings)
        if not validation.valid or not validation.restore_allowed:
            errors.extend(validation.errors)
            if not errors:
                errors.append("Restore is not allowed for this backup.")
            raise RepositoryError("Backup validation failed. Resolve errors before restoring.")

        from webstudio_backend.services.backup_alert_service import BackupAlertService

        alerts = BackupAlertService(self._session)
        data_only_restore = False
        if restore_scope == "entire_database":
            manifest = await self._load_manifest(filename)
            data_only_restore = manifest.get("database_dump_mode") == DATABASE_DUMP_MODE_DATA_ONLY

        if create_emergency_backup is None:
            create_emergency_backup = restore_scope == "entire_database" and not rollback

        run_snapshot: RestoreRunSnapshot | None = None

        async def _begin_restore_run() -> None:
            nonlocal run_snapshot
            await alerts.notify_restore_started(
                filename=filename,
                restore_scope=restore_scope,
            )
            run = await self._runs.create_run(
                filename=filename,
                source=source,
                restore_scope=restore_scope,
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
            )
            run_snapshot = RestoreRunSnapshot(
                id=run.id,
                filename=filename,
                source=source,
                restore_scope=restore_scope,
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
            )

        if not data_only_restore:
            await _begin_restore_run()

        try:
            if create_emergency_backup:
                emergency = await self._backup_engine.create_backup(
                    backup_type="full",
                    trigger_type="emergency",
                    creator_user_id=actor_user_id,
                    creator_display_name=actor_display_name or "System",
                )
                emergency_filename = emergency.filename
                warnings.append(f"Emergency backup created: {emergency_filename}")

            if restore_scope == "entire_database":
                if data_only_restore:
                    await truncate_webstudio_data(self._session)
                self._backup_engine.restore_backup(filename)
                self._session.expire_all()
                if data_only_restore:
                    await _begin_restore_run()
            elif restore_scope in {"settings_only", "company_config"}:
                await self._restore_settings_from_archive(filename, restore_scope)
            else:
                raise RepositoryError(f"Restore scope '{restore_scope}' is not yet implemented.")

            manifest = await self._load_manifest(filename)
            verification_status, verification_checks, verify_warnings = await self._verify_restore(
                filename,
                restore_scope,
                expected_manifest=manifest,
            )
            warnings.extend(verify_warnings)
            duration_ms = int((time.perf_counter() - started) * 1000)
            success = verification_status != "failed"
            rollback_recommended = not success and emergency_filename is not None
            if rollback_recommended:
                warnings.append(
                    f"Restore verification failed. Rollback available via emergency backup "
                    f"'{emergency_filename}'.",
                )

            check_payload = [
                {"key": c.key, "name": c.name, "status": c.status, "message": c.message}
                for c in verification_checks
            ]

            assert run_snapshot is not None
            await self._runs.mark_completed(
                run_snapshot,
                emergency_backup_filename=emergency_filename,
                duration_ms=duration_ms,
                verification_status=verification_status,
                warnings=warnings,
                errors=errors,
            )
            await self._audit_restore(
                filename=filename,
                restore_scope=restore_scope,
                source=source,
                emergency_backup_filename=emergency_filename,
                verification_status=verification_status,
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
                success=success,
                rollback=rollback,
            )
            await alerts.notify_recovery_completed(
                filename=filename,
                restore_scope=restore_scope,
                verification_status=verification_status,
            )
            if not success:
                await alerts.notify_restore_failed(
                    filename=filename,
                    restore_scope=restore_scope,
                    detail="Post-restore verification failed.",
                )
            await self._session.commit()

            return RestoreResult(
                success=success,
                filename=filename,
                restore_scope=restore_scope,
                emergency_backup_filename=emergency_filename,
                rollback_available=emergency_filename is not None,
                rollback_recommended=rollback_recommended,
                verification_status=verification_status,
                duration_ms=duration_ms,
                warnings=warnings,
                errors=errors,
                restart_required=restore_scope == "entire_database",
                verification_checks=check_payload,
            )
        except Exception as exc:
            errors.append(str(exc))
            if run_snapshot is None:
                await _begin_restore_run()
            assert run_snapshot is not None
            await self._runs.mark_completed(
                run_snapshot,
                emergency_backup_filename=emergency_filename,
                duration_ms=int((time.perf_counter() - started) * 1000),
                verification_status="failed",
                warnings=warnings,
                errors=errors,
            )
            await self._audit_restore(
                filename=filename,
                restore_scope=restore_scope,
                source=source,
                emergency_backup_filename=emergency_filename,
                verification_status="failed",
                actor_user_id=actor_user_id,
                actor_display_name=actor_display_name,
                success=False,
                rollback=rollback,
            )
            await alerts.notify_restore_failed(
                filename=filename,
                restore_scope=restore_scope,
                detail=str(exc),
            )
            await self._session.commit()
            raise RepositoryError(f"Restore failed: {exc}") from exc

    async def rollback_restore(
        self,
        *,
        emergency_backup_filename: str,
        confirmed: bool = False,
        actor_user_id: int | None = None,
        actor_display_name: str | None = None,
    ) -> RestoreResult:
        if not confirmed:
            raise RepositoryError("Rollback requires explicit confirmation.")
        return await self.execute_restore(
            filename=emergency_backup_filename,
            restore_scope="entire_database",
            source="emergency",
            create_emergency_backup=False,
            confirmed=True,
            actor_user_id=actor_user_id,
            actor_display_name=actor_display_name,
            rollback=True,
        )

    def import_backup_file(self, content: bytes, original_name: str) -> ImportBackupResult:
        if not content:
            raise RepositoryError("Imported backup file is empty.")
        if len(content) > 512 * 1024 * 1024:
            raise RepositoryError("Imported backup exceeds maximum size (512 MB).")

        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        extension = detect_import_extension(content, original_name)
        filename = f"webstudio-import-{stamp}{extension}"
        target = self._backup_root / filename
        self._backup_root.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

        try:
            loader = detect_backup_format(target)
            inspection = loader.inspect(target)
            if inspection.corruption_detected or not inspection.integrity_valid:
                target.unlink(missing_ok=True)
                detail = (
                    "; ".join(inspection.errors) or "Imported file is not a valid backup archive."
                )
                raise RepositoryError(detail)
        except RepositoryError:
            if target.is_file():
                target.unlink(missing_ok=True)
            raise
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise RepositoryError("Imported file is not a valid backup archive.") from exc

        loader = detect_backup_format(target)
        return ImportBackupResult(
            filename=filename,
            backup_format_id=loader.format_id,
            backup_format_label=loader.format_label,
        )

    def _resolve_archive_path(self, filename: str) -> Path:
        path = self._backup_root / filename
        if not is_supported_backup_path(path):
            raise RepositoryError("Invalid backup filename")
        return path

    async def _verify_checksum(
        self,
        filename: str,
        archive_path: Path,
        manifest: dict[str, Any],
    ) -> bool:
        run = await self._backup_runs.get_by_filename(filename)
        if run and run.checksum_sha256:
            actual = self._backup_engine._checksum_file(archive_path)  # noqa: SLF001
            return actual == run.checksum_sha256
        expected = manifest.get("checksum")
        if expected and manifest.get("checksum_algorithm") == "sha256":
            return True
        return bool(expected)

    def _compatibility_status(
        self,
        backup_app_version: str | None,
        backup_schema_version: str | None,
        current_schema: str,
    ) -> str:
        if backup_schema_version and backup_schema_version != current_schema:
            if backup_schema_version == "unknown" or current_schema == "unknown":
                return "warning"
            return "warning"
        if backup_app_version and backup_app_version != self._settings.app_version:
            return "warning"
        return "compatible"

    async def _load_manifest(self, filename: str) -> dict[str, Any]:
        archive_path = self._resolve_archive_path(filename)
        loader = detect_backup_format(archive_path)
        if loader.format_id == FORMAT_LEGACY_SQL:
            return {}
        return loader.read_manifest(archive_path)

    def _affected_areas(self, restore_scope: str) -> list[str]:
        mapping = {
            "entire_database": [
                "PostgreSQL database",
                "Company settings",
                "Users and roles",
                "Security settings",
                "Integrations",
                "Tally configuration",
            ],
            "settings_only": ["System settings registry"],
            "company_config": ["Company profile", "Branding", "Regional defaults"],
            "users_only": ["User accounts", "Roles and permissions"],
            "reports_only": ["Report templates"],
        }
        return mapping.get(restore_scope, [])

    async def _restore_settings_from_archive(self, filename: str, restore_scope: str) -> None:
        archive_path = self._resolve_archive_path(filename)
        with tempfile.TemporaryDirectory(prefix="webstudio-restore-settings-") as temp_dir:
            workspace = Path(temp_dir)
            inspection = detect_backup_format(archive_path).extract(archive_path, workspace)
            if inspection.corruption_detected or not inspection.integrity_valid:
                detail = "; ".join(inspection.errors) or "Archive integrity check failed."
                raise RepositoryError(detail)
            settings_path = workspace / "config" / "settings-registry.json"
            if not settings_path.is_file():
                raise RepositoryError("Backup archive is missing settings-registry.json")
            snapshot = json.loads(settings_path.read_text(encoding="utf-8"))
            keys = self._settings_keys_for_scope(restore_scope)
            for key in keys:
                if key not in snapshot or key in SETTINGS_EXCLUDED_KEYS:
                    continue
                default_type = SETTING_DEFAULTS.get(key, ("", SettingValueType.STRING))[1]
                await self._settings_repo.set_value(
                    key,
                    str(snapshot[key]),
                    value_type=default_type,
                )
            if restore_scope == "company_config":
                company_assets = workspace / "assets" / "company"
                if company_assets.is_dir():
                    for logo_file in company_assets.iterdir():
                        if logo_file.is_file():
                            target_dir = self._backup_engine._find_repo_root()  # noqa: SLF001
                            if target_dir is not None:
                                dest = target_dir / "apps/desktop/public/assets/company"
                                dest.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(logo_file, dest / logo_file.name)

    def _settings_keys_for_scope(self, restore_scope: str) -> set[str]:
        if restore_scope == "company_config":
            return set(COMPANY_CONFIG_KEYS)
        return {key for key in SETTING_DEFAULTS if key not in SETTINGS_EXCLUDED_KEYS}

    async def _verify_restore(
        self,
        filename: str,
        restore_scope: str,
        *,
        expected_manifest: dict[str, Any] | None = None,
    ) -> tuple[str, list, list[str]]:
        _ = filename
        status, checks, warnings = await verify_post_restore(
            self._session,
            self._settings_repo,
            restore_scope=restore_scope,
            expected_manifest=expected_manifest,
        )
        return status, checks, warnings

    async def _audit_restore(
        self,
        *,
        filename: str,
        restore_scope: str,
        source: str,
        emergency_backup_filename: str | None,
        verification_status: str,
        actor_user_id: int | None,
        actor_display_name: str | None,
        success: bool,
        rollback: bool,
    ) -> None:
        actor = AuditActor(
            user_id=actor_user_id,
            display_name=actor_display_name or "System",
            role="main_admin" if actor_user_id else "system",
        )
        await self._recorder.record_restore_operation(
            filename=filename,
            restore_scope=restore_scope,
            source=source,
            emergency_backup_filename=emergency_backup_filename,
            verification_status=verification_status,
            actor=actor,
            success=success,
            rollback=rollback,
        )
