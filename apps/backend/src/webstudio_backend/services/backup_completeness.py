"""Complete business-state backup catalog, snapshots, and restore preparation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.constants import DATABASE_SCHEMA
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

BACKUP_DATABASE_TABLES = (
    "audit_logs",
    "backup_runs",
    "brands",
    "integration_api_keys",
    "inventory_items",
    "locations",
    "login_events",
    "notifications",
    "password_history",
    "product_models",
    "refresh_tokens",
    "restore_runs",
    "sales",
    "system_settings",
    "tally_company_sync",
    "tally_processed_invoice",
    "tally_processed_invoice_line",
    "tally_sync_log",
    "tally_sync_history",
    "users",
)

BACKUP_MANAGED_ASSET_DIRS = (
    "brand-logos",
    "product-images",
    "company",
    "uploads",
)

MANUAL_BACKUP_RECOMMENDATION = (
    "Although automatic backups are maintained internally, it is recommended to create "
    "and safely store an external manual backup (weekly or monthly) so your business can "
    "be fully recovered even if the primary system or storage device fails."
)

DATABASE_DUMP_MODE_DATA_ONLY = "data_only"
DATABASE_DUMP_MODE_FULL = "full"


def use_real_database_dump() -> bool:
    return os.environ.get("WEBSTUDIO_BACKUP_REAL_DUMP", "").lower() in {"1", "true", "yes"}


@dataclass(frozen=True, slots=True)
class BusinessSnapshot:
    company_name: str
    inventory_count: int
    serial_numbers: tuple[str, ...]
    sales_count: int
    users_count: int
    audit_log_count: int
    notification_count: int
    brands_count: int
    locations_count: int
    product_models_count: int
    product_image_count: int
    integration_api_key_count: int
    tally_company_name: str
    gemini_model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "inventory_count": self.inventory_count,
            "serial_numbers": list(self.serial_numbers),
            "sales_count": self.sales_count,
            "users_count": self.users_count,
            "audit_log_count": self.audit_log_count,
            "notification_count": self.notification_count,
            "brands_count": self.brands_count,
            "locations_count": self.locations_count,
            "product_models_count": self.product_models_count,
            "product_image_count": self.product_image_count,
            "integration_api_key_count": self.integration_api_key_count,
            "tally_company_name": self.tally_company_name,
            "gemini_model": self.gemini_model,
        }


async def collect_extended_backup_stats(session: AsyncSession) -> dict[str, int]:
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
    product_images = int(
        (
            await session.execute(
                select(func.count(ProductModel.id)).where(ProductModel.product_image_url.is_not(None)),
            )
        ).scalar_one()
        or 0,
    )
    size_result = await session.execute(text("SELECT pg_database_size(current_database())"))
    db_size = int(size_result.scalar_one() or 0)
    return {
        "database_size_bytes": db_size,
        "inventory_count": inventory,
        "serial_numbers_count": inventory,
        "sales_count": sales,
        "users_count": users,
        "audit_log_count": audits,
        "notification_count": notifications,
        "brands_count": brands,
        "locations_count": locations,
        "product_models_count": product_models,
        "product_image_count": product_images,
        "integration_api_key_count": integration_keys,
    }


async def collect_business_snapshot(
    session: AsyncSession,
    settings_repo: SystemSettingRepository,
) -> BusinessSnapshot:
    stats = await collect_extended_backup_stats(session)
    serials = (
        await session.execute(
            select(InventoryItem.serial_number).order_by(InventoryItem.serial_number),
        )
    ).scalars().all()
    return BusinessSnapshot(
        company_name=await settings_repo.get_string("company_name") or "",
        inventory_count=stats["inventory_count"],
        serial_numbers=tuple(serials),
        sales_count=stats["sales_count"],
        users_count=stats["users_count"],
        audit_log_count=stats["audit_log_count"],
        notification_count=stats["notification_count"],
        brands_count=stats["brands_count"],
        locations_count=stats["locations_count"],
        product_models_count=stats["product_models_count"],
        product_image_count=stats["product_image_count"],
        integration_api_key_count=stats["integration_api_key_count"],
        tally_company_name=await settings_repo.get_string("tally_company_name") or "",
        gemini_model=await settings_repo.get_string("gemini_model") or "",
    )


def compare_business_snapshots(
    before: BusinessSnapshot,
    after: BusinessSnapshot,
) -> list[str]:
    mismatches: list[str] = []
    before_dict = before.as_dict()
    after_dict = after.as_dict()
    for key, label in (
        ("company_name", "Company name"),
        ("inventory_count", "Inventory count"),
        ("sales_count", "Sales count"),
        ("users_count", "Users count"),
        ("audit_log_count", "Audit log count"),
        ("notification_count", "Notification count"),
        ("brands_count", "Brands count"),
        ("locations_count", "Locations count"),
        ("product_models_count", "Product models count"),
        ("product_image_count", "Product image count"),
        ("integration_api_key_count", "Integration API key count"),
        ("tally_company_name", "Tally company name"),
        ("gemini_model", "Gemini model"),
    ):
        if before_dict[key] != after_dict[key]:
            mismatches.append(f"{label}: expected {before_dict[key]!r}, got {after_dict[key]!r}")
    if list(before.serial_numbers) != list(after.serial_numbers):
        mismatches.append(
            f"Serial numbers differ: expected {len(before.serial_numbers)}, "
            f"got {len(after.serial_numbers)}",
        )
    return mismatches


async def truncate_webstudio_data(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = :schema AND tablename != 'alembic_version'
            """,
        ),
        {"schema": DATABASE_SCHEMA},
    )
    tables = [row[0] for row in result.fetchall()]
    if not tables:
        return
    quoted = ", ".join(f'"{DATABASE_SCHEMA}"."{table}"' for table in tables)
    await session.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    await session.commit()


async def verify_foreign_key_integrity(session: AsyncSession) -> tuple[bool, str]:
    result = await session.execute(
        text(
            """
            SELECT COUNT(*) FROM (
                SELECT conname
                FROM pg_constraint
                WHERE connamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname = :schema
                )
                AND contype = 'f'
                AND NOT convalidated
            ) AS invalid
            """,
        ),
        {"schema": DATABASE_SCHEMA},
    )
    invalid = int(result.scalar_one() or 0)
    if invalid:
        return False, f"{invalid} foreign key constraint(s) are not validated."
    return True, "Foreign key constraints are valid."


def count_local_asset_files(assets_root: Path | None) -> int:
    if assets_root is None or not assets_root.is_dir():
        return 0
    count = 0
    for subdir in BACKUP_MANAGED_ASSET_DIRS:
        folder = assets_root / subdir
        if folder.is_dir():
            count += sum(
                1 for item in folder.iterdir() if item.is_file() and item.name != ".gitkeep"
            )
    return count
