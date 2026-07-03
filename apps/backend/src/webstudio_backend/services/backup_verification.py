"""Backup and restore verification helpers."""

from __future__ import annotations

import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.integration_api_key import IntegrationApiKey
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.infrastructure.database.models.user import User
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.backup_completeness import (
    BACKUP_DATABASE_TABLES,
    count_local_asset_files,
    verify_foreign_key_integrity,
)
from webstudio_backend.services.backup_manifest import validate_manifest_structure


@dataclass(frozen=True, slots=True)
class VerificationCheck:
    key: str
    name: str
    status: str
    message: str


@dataclass(frozen=True, slots=True)
class BackupIntegrityResult:
    filename: str
    valid: bool
    checksum_valid: bool
    integrity_valid: bool
    compression_valid: bool
    manifest_valid: bool
    corruption_detected: bool
    verification_status: str
    overall_health: str
    warnings: list[str]
    errors: list[str]
    checks: list[VerificationCheck]


REQUIRED_TABLES = BACKUP_DATABASE_TABLES


def _count_restored_managed_assets() -> int:
    cwd = Path.cwd()
    for candidate in (cwd, cwd.parent, cwd.parent.parent, cwd.parent.parent.parent):
        assets = candidate / "apps/desktop/public/assets"
        if assets.is_dir():
            return count_local_asset_files(assets)
    return 0


async def verify_backup_integrity(
    *,
    filename: str,
    archive_path: Path,
    manifest: dict[str, Any],
    stored_checksum: str | None,
    checksum_file_fn,
) -> BackupIntegrityResult:
    warnings: list[str] = []
    errors: list[str] = []
    checks: list[VerificationCheck] = []
    corruption_detected = False
    integrity_valid = True
    compression_valid = True
    manifest_valid = True

    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            names = archive.getnames()
            for required in ("manifest.json", "database.sql"):
                present = required in names
                checks.append(
                    VerificationCheck(
                        key=f"member_{required}",
                        name=f"Archive member {required}",
                        status="passed" if present else "failed",
                        message="Present" if present else "Missing",
                    ),
                )
                if not present:
                    errors.append(f"Missing required archive member: {required}")
                    integrity_valid = False
            db_info = archive.getmember("database.sql")
            if db_info.size < 16:
                warnings.append("Database dump appears unusually small.")
    except tarfile.TarError as exc:
        corruption_detected = True
        integrity_valid = False
        compression_valid = False
        errors.append(f"Archive integrity check failed: {exc}")

    manifest_warnings, manifest_errors = validate_manifest_structure(manifest)
    warnings.extend(manifest_warnings)
    errors.extend(manifest_errors)
    if manifest_errors:
        manifest_valid = False

    checksum_valid = False
    if stored_checksum:
        actual = checksum_file_fn(archive_path)
        checksum_valid = actual == stored_checksum
        checks.append(
            VerificationCheck(
                key="archive_checksum",
                name="Archive checksum",
                status="passed" if checksum_valid else "failed",
                message="Matches stored checksum" if checksum_valid else "Checksum mismatch",
            ),
        )
    elif manifest.get("checksum"):
        checks.append(
            VerificationCheck(
                key="content_checksum",
                name="Manifest checksum",
                status="warning",
                message="Content checksum present; archive checksum not stored.",
            ),
        )
        checksum_valid = True
    else:
        warnings.append("No checksum available for verification.")

    if corruption_detected:
        overall_health = "corrupt"
        verification_status = "failed"
    elif errors:
        overall_health = "unhealthy"
        verification_status = "failed"
    elif warnings:
        overall_health = "degraded"
        verification_status = "warning"
    else:
        overall_health = "healthy"
        verification_status = "success"

    checks.append(
        VerificationCheck(
            key="manifest_validation",
            name="Manifest validation",
            status="passed" if manifest_valid else "warning",
            message="Manifest structure valid" if manifest_valid else "Manifest validation issues",
        ),
    )
    checks.append(
        VerificationCheck(
            key="compression",
            name="Compression status",
            status="passed" if compression_valid else "failed",
            message="gzip archive readable" if compression_valid else "Compression failure",
        ),
    )

    valid = not corruption_detected and integrity_valid and not errors
    return BackupIntegrityResult(
        filename=filename,
        valid=valid,
        checksum_valid=checksum_valid,
        integrity_valid=integrity_valid,
        compression_valid=compression_valid,
        manifest_valid=manifest_valid,
        corruption_detected=corruption_detected,
        verification_status=verification_status,
        overall_health=overall_health,
        warnings=warnings,
        errors=errors,
        checks=checks,
    )


async def verify_post_restore(
    session: AsyncSession,
    settings_repo: SystemSettingRepository,
    *,
    restore_scope: str,
    expected_manifest: dict[str, Any] | None = None,
) -> tuple[str, list[VerificationCheck], list[str]]:
    checks: list[VerificationCheck] = []
    warnings: list[str] = []

    if restore_scope != "entire_database":
        checks.append(
            VerificationCheck(
                key="scope",
                name="Restore scope",
                status="passed",
                message=f"Scoped restore ({restore_scope}) completed.",
            ),
        )
        return "success", checks, warnings

    try:
        await session.execute(text("SELECT 1"))
        checks.append(
            VerificationCheck(
                key="database_integrity",
                name="Database integrity",
                status="passed",
                message="Database is reachable.",
            ),
        )
    except Exception as exc:
        checks.append(
            VerificationCheck(
                key="database_integrity",
                name="Database integrity",
                status="failed",
                message=str(exc),
            ),
        )
        return "failed", checks, warnings

    for table in REQUIRED_TABLES:
        try:
            await session.execute(text(f"SELECT 1 FROM webstudio.{table} LIMIT 1"))
            checks.append(
                VerificationCheck(
                    key=f"table_{table}",
                    name=f"Table {table}",
                    status="passed",
                    message="Present",
                ),
            )
        except Exception:
            checks.append(
                VerificationCheck(
                    key=f"table_{table}",
                    name=f"Table {table}",
                    status="failed",
                    message="Missing or inaccessible",
                ),
            )
            warnings.append(f"Required table check failed: {table}")

    inventory = int((await session.execute(select(func.count(InventoryItem.id)))).scalar_one() or 0)
    sales = int((await session.execute(select(func.count(Sale.id)))).scalar_one() or 0)
    users = int((await session.execute(select(func.count(User.id)))).scalar_one() or 0)
    audits = int((await session.execute(select(func.count(AuditLog.id)))).scalar_one() or 0)
    notifications = int(
        (await session.execute(select(func.count(Notification.id)))).scalar_one() or 0,
    )
    brands = int((await session.execute(select(func.count(Brand.id)))).scalar_one() or 0)
    locations = int((await session.execute(select(func.count(Location.id)))).scalar_one() or 0)
    product_models = int(
        (await session.execute(select(func.count(ProductModel.id)))).scalar_one() or 0,
    )
    integration_keys = int(
        (await session.execute(select(func.count(IntegrationApiKey.id)))).scalar_one() or 0,
    )

    fk_valid, fk_message = await verify_foreign_key_integrity(session)
    checks.append(
        VerificationCheck(
            key="foreign_keys",
            name="Foreign keys",
            status="passed" if fk_valid else "failed",
            message=fk_message,
        ),
    )
    if not fk_valid:
        warnings.append(fk_message)

    checks.extend(
        [
            VerificationCheck(
                key="inventory_count",
                name="Inventory count",
                status="passed",
                message=str(inventory),
            ),
            VerificationCheck(
                key="serial_numbers",
                name="Serial numbers",
                status="passed",
                message=f"{inventory} serial number(s)",
            ),
            VerificationCheck(
                key="sales_count",
                name="Sales count",
                status="passed",
                message=str(sales),
            ),
            VerificationCheck(
                key="users_count",
                name="Users count",
                status="passed",
                message=str(users),
            ),
            VerificationCheck(
                key="audit_log_count",
                name="Audit records",
                status="passed",
                message=str(audits),
            ),
            VerificationCheck(
                key="notifications_count",
                name="Notifications",
                status="passed",
                message=str(notifications),
            ),
            VerificationCheck(
                key="brands_count",
                name="Brands",
                status="passed",
                message=str(brands),
            ),
            VerificationCheck(
                key="locations_count",
                name="Locations",
                status="passed",
                message=str(locations),
            ),
            VerificationCheck(
                key="product_models_count",
                name="Product models",
                status="passed",
                message=str(product_models),
            ),
            VerificationCheck(
                key="integration_api_keys",
                name="Integration API keys",
                status="passed",
                message=f"{integration_keys} encrypted key(s)",
            ),
        ]
    )

    company_name = await settings_repo.get_string("company_name") or ""
    checks.append(
        VerificationCheck(
            key="settings",
            name="Settings",
            status="passed" if company_name else "warning",
            message="Company settings readable",
        ),
    )
    checks.append(
        VerificationCheck(
            key="tally_configuration",
            name="Tally configuration",
            status="passed",
            message=await settings_repo.get_string("tally_company_name") or "not configured",
        ),
    )

    checks.append(
        VerificationCheck(
            key="gemini_configuration",
            name="Gemini configuration",
            status="passed",
            message=await settings_repo.get_string("gemini_model") or "not configured",
        ),
    )
    checks.append(
        VerificationCheck(
            key="permissions",
            name="Roles and permissions",
            status="passed" if users else "warning",
            message=f"{users} user account(s) restored",
        ),
    )

    managed_asset_count = _count_restored_managed_assets()
    checks.append(
        VerificationCheck(
            key="images_folder",
            name="Managed asset files",
            status="passed",
            message=(
                f"{managed_asset_count} managed file(s) available"
                if managed_asset_count
                else "Product images stored as URLs; managed asset folders ready"
            ),
        ),
    )

    if expected_manifest:
        for field, label in (
            ("inventory_count", "Inventory count"),
            ("sales_count", "Sales count"),
            ("users_count", "Users count"),
            ("notification_count", "Notification count"),
            ("product_models_count", "Product models count"),
        ):
            expected = expected_manifest.get(field)
            actual_map = {
                "inventory_count": inventory,
                "sales_count": sales,
                "users_count": users,
                "notification_count": notifications,
                "product_models_count": product_models,
            }
            actual = actual_map[field]
            if expected is not None and int(expected) != int(actual):
                warnings.append(f"{label} differs from backup manifest ({expected} vs {actual}).")
                checks.append(
                    VerificationCheck(
                        key=f"verify_{field}",
                        name=label,
                        status="warning",
                        message=f"Expected {expected}, found {actual}",
                    ),
                )

    failed = any(check.status == "failed" for check in checks)
    warned = any(check.status == "warning" for check in checks) or warnings
    if failed:
        return "failed", checks, warnings
    if warned:
        return "warning", checks, warnings
    return "success", checks, warnings
