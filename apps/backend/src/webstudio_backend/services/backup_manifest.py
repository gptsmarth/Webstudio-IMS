"""Backup manifest — metadata schema, stats collection, and validation."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_completeness import (
    DATABASE_DUMP_MODE_DATA_ONLY,
    collect_extended_backup_stats,
)

MANIFEST_FORMAT_VERSION = 2
BACKUP_VERSION = "2.1"
SUPPORTED_BACKUP_VERSIONS = frozenset({"1.0", "2.0", "2.1"})


async def collect_backup_stats(session: AsyncSession) -> dict[str, int]:
    return await collect_extended_backup_stats(session)


async def config_version_hash(settings_repo: SystemSettingRepository, keys: tuple[str, ...]) -> str:
    parts: list[str] = []
    for key in keys:
        value = await settings_repo.get_string(key) or ""
        parts.append(f"{key}={value}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:16]


async def build_manifest(
    *,
    settings_repo: SystemSettingRepository,
    session: AsyncSession,
    backup_type: str,
    trigger_type: str,
    creator_display_name: str | None,
    schema_version: str,
    app_version: str,
    api_version: str,
    storage_backend: str,
    base_backup_id: int | None,
    backup_run_id: int,
    encrypted: bool = False,
    database_dump_mode: str = DATABASE_DUMP_MODE_DATA_ONLY,
    managed_asset_file_count: int = 0,
) -> dict[str, Any]:
    stats = await collect_backup_stats(session)
    company_name = await settings_repo.get_string("company_name") or ""
    tally_keys = (
        "tally_enabled",
        "tally_host",
        "tally_port",
        "tally_company_name",
        "tally_sync_interval_seconds",
    )
    tally_version = await config_version_hash(settings_repo, tally_keys)
    gemini_version = await config_version_hash(
        settings_repo,
        ("gemini_model", "gemini_api_key"),
    )
    return {
        "format_version": MANIFEST_FORMAT_VERSION,
        "backup_version": BACKUP_VERSION,
        "backup_type": backup_type,
        "trigger_type": trigger_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "schema_version": schema_version,
        "app_version": app_version,
        "api_version": api_version,
        "creator": creator_display_name or "System",
        "created_by": creator_display_name or "System",
        "created_date": datetime.now(UTC).isoformat(),
        "company_name": company_name,
        "database_size_bytes": stats["database_size_bytes"],
        "backup_size_bytes": 0,
        "inventory_count": stats["inventory_count"],
        "sales_count": stats["sales_count"],
        "users_count": stats["users_count"],
        "audit_log_count": stats["audit_log_count"],
        "notification_count": stats["notification_count"],
        "serial_numbers_count": stats["serial_numbers_count"],
        "brands_count": stats["brands_count"],
        "locations_count": stats["locations_count"],
        "product_models_count": stats["product_models_count"],
        "product_image_count": stats["product_image_count"],
        "integration_api_key_count": stats["integration_api_key_count"],
        "managed_asset_file_count": managed_asset_file_count,
        "database_dump_mode": database_dump_mode,
        "checksum": "",
        "checksum_algorithm": "sha256",
        "tally_configuration_version": tally_version,
        "gemini_configuration_version": gemini_version,
        "backup_run_id": backup_run_id,
        "contents": [
            "postgresql_database",
            "inventory",
            "serial_numbers",
            "product_models",
            "brands",
            "locations",
            "sales",
            "customers",
            "audit_logs",
            "notifications",
            "users",
            "roles_permissions",
            "login_history",
            "session_data",
            "security_settings",
            "system_settings",
            "company_information",
            "backup_history",
            "restore_history",
            "report_configurations",
            "tally_configuration",
            "gemini_configuration",
            "encrypted_api_keys",
            "integration_settings",
            "brand_logos",
            "product_images",
            "uploaded_assets",
            "branding_assets",
            "application_configuration",
        ],
        "excluded": ["logs", "cache", "temporary_files"],
        "storage_backend": storage_backend,
        "base_backup_id": base_backup_id,
        "encrypted": encrypted,
        "encryption_algorithm": None,
        "compression": "gzip",
    }


def finalize_manifest(
    manifest: dict[str, Any],
    *,
    backup_size_bytes: int,
    content_checksum: str,
    duration_ms: int,
) -> dict[str, Any]:
    updated = dict(manifest)
    updated["backup_size_bytes"] = backup_size_bytes
    updated["duration_ms"] = duration_ms
    updated["checksum"] = content_checksum
    return updated


def compute_content_checksum(*file_paths: tuple[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, payload in sorted(file_paths, key=lambda item: item[0]):
        digest.update(name.encode("utf-8"))
        digest.update(payload)
    return digest.hexdigest()


def validate_manifest_structure(manifest: dict[str, Any]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    required = (
        "app_version",
        "schema_version",
        "backup_version",
        "backup_type",
        "created_by",
        "created_date",
        "company_name",
        "checksum_algorithm",
    )
    for field in required:
        if not manifest.get(field) and manifest.get(field) != 0:
            warnings.append(f"Manifest missing recommended field: {field}")
    backup_version = str(manifest.get("backup_version", "1.0"))
    if backup_version not in SUPPORTED_BACKUP_VERSIONS:
        warnings.append(f"Unsupported backup version: {backup_version}")
    if manifest.get("encrypted") and not manifest.get("encryption_algorithm"):
        warnings.append("Archive marked encrypted but encryption_algorithm is missing.")
    return warnings, errors


def manifest_preview_fields(manifest: dict[str, Any], *, size_bytes: int) -> dict[str, Any]:
    return {
        "backup_name": manifest.get("filename"),
        "company_name": manifest.get("company_name"),
        "created_date": manifest.get("created_date") or manifest.get("timestamp"),
        "created_by": manifest.get("created_by") or manifest.get("creator"),
        "app_version": manifest.get("app_version"),
        "backup_version": manifest.get("backup_version"),
        "schema_version": manifest.get("schema_version"),
        "inventory_count": manifest.get("inventory_count"),
        "sales_count": manifest.get("sales_count"),
        "users_count": manifest.get("users_count"),
        "audit_log_count": manifest.get("audit_log_count"),
        "notification_count": manifest.get("notification_count"),
        "product_image_count": manifest.get("product_image_count"),
        "managed_asset_file_count": manifest.get("managed_asset_file_count"),
        "database_dump_mode": manifest.get("database_dump_mode"),
        "database_size_bytes": manifest.get("database_size_bytes"),
        "compressed_size_bytes": manifest.get("backup_size_bytes") or size_bytes,
        "checksum": manifest.get("checksum"),
        "tally_configuration_version": manifest.get("tally_configuration_version"),
        "gemini_configuration_version": manifest.get("gemini_configuration_version"),
    }


def _revision_sort_key(version: str) -> tuple[int, str]:
    if not version or version == "unknown":
        return (-1, version)
    prefix = version.split("_", 1)[0]
    if prefix.isdigit():
        return (int(prefix), version)
    return (0, version)


def compatibility_report(
    manifest: dict[str, Any],
    *,
    current_app_version: str,
    current_schema_version: str,
    corruption_detected: bool,
    integrity_valid: bool,
) -> dict[str, Any]:
    backup_app = str(manifest.get("app_version") or "")
    backup_schema = str(manifest.get("schema_version") or "")
    backup_version = str(manifest.get("backup_version") or "1.0")
    app_match = not backup_app or backup_app == current_app_version
    backup_key = _revision_sort_key(backup_schema)
    current_key = _revision_sort_key(current_schema_version)
    schema_match = not backup_schema or backup_schema == current_schema_version
    backup_schema_newer = bool(
        backup_schema
        and current_schema_version
        and not schema_match
        and backup_key > current_key
    )
    migration_required = bool(
        backup_schema
        and current_schema_version
        and not schema_match
        and backup_key < current_key
    )
    version_supported = backup_version in SUPPORTED_BACKUP_VERSIONS
    backward_compatible = version_supported and not backup_schema_newer
    restore_allowed = (
        integrity_valid
        and not corruption_detected
        and version_supported
        and not backup_schema_newer
        and (schema_match or migration_required or not backup_schema)
    )
    if corruption_detected or not integrity_valid:
        summary = "Restore blocked: archive integrity failure."
    elif not version_supported:
        summary = "Restore blocked: unsupported backup version."
    elif backup_schema_newer:
        summary = (
            "Restore blocked: backup was created with a newer database schema. "
            "Upgrade WEBSTUDIO IMS before restoring."
        )
    elif migration_required:
        summary = "Restore allowed with caution: database migration may be required after restore."
    elif not app_match:
        summary = "Restore allowed with caution: application version differs."
    else:
        summary = "Restore is compatible with the current system."
    return {
        "app_version_match": app_match,
        "schema_version_match": schema_match,
        "backup_version_supported": version_supported,
        "migration_required": migration_required,
        "backup_schema_newer": backup_schema_newer,
        "backward_compatible": backward_compatible,
        "restore_allowed": restore_allowed,
        "summary": summary,
        "backup_app_version": backup_app or None,
        "backup_schema_version": backup_schema or None,
        "current_app_version": current_app_version,
        "current_schema_version": current_schema_version,
        "backup_version": backup_version,
    }
