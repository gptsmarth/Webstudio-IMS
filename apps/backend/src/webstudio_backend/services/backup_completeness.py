"""Complete business-state backup catalog, snapshots, and restore preparation."""

from __future__ import annotations

import os
import re
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
from webstudio_backend.infrastructure.repositories.exceptions import RepositoryError
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
ALEMBIC_VERSION_TABLE = "alembic_version"
_IDENTIFIER = r'(?:"[a-z_][a-z0-9_]*"|[a-z_][a-z0-9_]*)'
_DUMP_RELATION = rf'(?:"webstudio"|webstudio)\.{_IDENTIFIER}'
_DUMP_COPY = re.compile(rf"COPY {_DUMP_RELATION} \({_IDENTIFIER}(?:, {_IDENTIFIER})*\) FROM stdin;")
_DUMP_SEQUENCE = re.compile(
    rf"SELECT pg_catalog\.setval\('({_DUMP_RELATION})', (-?\d+), (true|false)\);"
)
_DUMP_TRIGGER = re.compile(
    rf"ALTER TABLE (?:ONLY )?{_DUMP_RELATION} (?:DISABLE|ENABLE) TRIGGER ALL;"
)
_DUMP_SETTINGS = {
    "SET statement_timeout = 0;",
    "SET lock_timeout = 0;",
    "SET idle_in_transaction_session_timeout = 0;",
    "SET client_encoding = 'UTF8';",
    "SET standard_conforming_strings = on;",
    "SELECT pg_catalog.set_config('search_path', '', false);",
    "SET check_function_bodies = false;",
    "SET xmloption = content;",
    "SET client_min_messages = warning;",
    "SET row_security = off;",
    "SET SESSION AUTHORIZATION DEFAULT;",
    "SET default_table_access_method = heap;",
    "SET default_tablespace = '';",
}
SNAPSHOT_COUNT_TABLES = {
    "inventory_count": "inventory_items",
    "sales_count": "sales",
    "users_count": "users",
    "product_models_count": "product_models",
}


def dump_snapshot_counts(path: Path) -> dict[str, int]:
    """Count rows from the same PostgreSQL snapshot as the SQL in the archive."""
    fields = {table: field for field, table in SNAPSHOT_COUNT_TABLES.items()}
    counts: dict[str, int] = {}
    in_copy = False
    field = None
    with path.open(encoding="utf-8") as dump:
        for line in dump:
            statement = line.rstrip("\r\n")
            if in_copy:
                if statement == r"\.":
                    in_copy = False
                elif field is not None:
                    counts[field] += 1
            elif _DUMP_COPY.fullmatch(statement):
                in_copy = True
                field = fields.get(statement.split()[1].replace('"', "").split(".")[1])
                if field is not None:
                    counts[field] = 0
    return counts if counts.keys() == SNAPSHOT_COUNT_TABLES.keys() else {}


def filter_alembic_version_copy_blocks(sql: str) -> str:
    """Drop alembic_version COPY blocks from a data-only pg_dump (schema state is not restored)."""
    lines = sql.splitlines(keepends=True)
    out: list[str] = []
    in_copy = False
    skip_copy = False
    for line in lines:
        stripped = line.strip()
        if in_copy:
            if not skip_copy:
                out.append(line)
            in_copy = stripped != r"\."
            continue
        if stripped.startswith("-- Data for Name: alembic_version;"):
            continue
        if stripped.startswith("COPY ") and stripped.endswith(" FROM stdin;"):
            in_copy = True
            table = stripped.split(maxsplit=2)[1].replace('"', "")
            skip_copy = table in {"alembic_version", f"{DATABASE_SCHEMA}.alembic_version"}
        if not in_copy or not skip_copy:
            out.append(line)
    return "".join(out)


def prepare_data_only_restore_sql(sql: str) -> str:
    """Accept PostgreSQL data-only COPY dumps for the IMS schema."""
    dump = filter_alembic_version_copy_blocks(sql)
    out: list[str] = []
    in_copy = False
    for number, line in enumerate(dump.splitlines(keepends=True), 1):
        statement = line.strip()
        if in_copy:
            in_copy = line.rstrip("\r\n") != r"\."
        elif _DUMP_COPY.fullmatch(statement):
            in_copy = True
        elif _DUMP_TRIGGER.fullmatch(statement) or re.fullmatch(
            r"\\(?:un)?restrict [a-zA-Z0-9]+", statement
        ):
            continue
        elif statement == "SET transaction_timeout = 0;":
            # pg_dump 17+ emits this even when it connects to PostgreSQL 16.
            line = (
                "SELECT pg_catalog.set_config('transaction_timeout', '0', false) "
                "WHERE pg_catalog.current_setting('server_version_num')::integer >= 170000;\n"
            )
        elif sequence := _DUMP_SEQUENCE.fullmatch(statement):
            name, value, called = sequence.groups()
            line = f"SELECT pg_temp.restore_sequence('{name}', {value}, {called});\n"
        elif statement not in _DUMP_SETTINGS and statement and not statement.startswith("--"):
            raise RepositoryError(f"Unsupported command on line {number} of the data-only dump.")
        out.append(line)
    if in_copy:
        raise RepositoryError("The backup contains an incomplete PostgreSQL COPY block.")
    return "".join(out)


# Only the owner can change FK timing. Keep the checks enabled and validate all
# pending rows before restoring the original constraints and committing.
DATA_ONLY_RESTORE_START = """
SET LOCAL search_path = pg_catalog;
SET LOCAL lock_timeout = '15s';
CREATE TEMP TABLE restore_immediate_fks ON COMMIT DROP AS
SELECT n.nspname AS schema_name, t.relname AS table_name, c.conname AS constraint_name
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'webstudio' AND c.contype = 'f' AND NOT c.condeferrable
  AND c.conparentid = 0;

CREATE FUNCTION pg_temp.restore_sequence(sequence_name regclass, seq_value bigint, called boolean)
RETURNS void LANGUAGE plpgsql AS $sequence$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_depend d
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE d.classid = 'pg_class'::regclass AND d.objid = sequence_name
          AND d.refclassid = 'pg_class'::regclass AND d.deptype IN ('a', 'i')
          AND n.nspname = 'webstudio' AND t.relname <> 'alembic_version'
          AND t.relkind IN ('r', 'p')
    ) THEN
        RAISE EXCEPTION 'Backup sequence is not owned by an IMS table';
    END IF;
    PERFORM pg_catalog.setval(sequence_name, seq_value, called);
END
$sequence$;

DO $restore$
DECLARE
    target_tables text;
    fk record;
BEGIN
    IF current_setting('webstudio.restore_revision', true) IS NOT NULL AND NOT EXISTS (
        SELECT FROM webstudio.alembic_version
        WHERE version_num = current_setting('webstudio.restore_revision')
    ) THEN
        RAISE EXCEPTION 'The destination migration revision changed; revalidate the backup';
    END IF;
    SELECT string_agg(format('%I.%I', schemaname, tablename), ', ' ORDER BY tablename)
    INTO target_tables
    FROM pg_tables
    WHERE schemaname = 'webstudio' AND tablename <> 'alembic_version';
    IF target_tables IS NULL THEN
        RAISE EXCEPTION 'Run the WEBSTUDIO database migrations before restoring data';
    END IF;
    EXECUTE 'TRUNCATE TABLE ' || target_tables || ' RESTART IDENTITY';
    FOR fk IN SELECT * FROM pg_temp.restore_immediate_fks ORDER BY table_name, constraint_name LOOP
        EXECUTE format('ALTER TABLE %I.%I ALTER CONSTRAINT %I DEFERRABLE INITIALLY IMMEDIATE',
                       fk.schema_name, fk.table_name, fk.constraint_name);
    END LOOP;
END
$restore$;
SET CONSTRAINTS ALL DEFERRED;
"""


DATA_ONLY_RESTORE_FINISH = """
SET CONSTRAINTS ALL IMMEDIATE;
DO $restore$
DECLARE
    fk record;
BEGIN
    FOR fk IN SELECT * FROM pg_temp.restore_immediate_fks ORDER BY table_name, constraint_name LOOP
        EXECUTE format('ALTER TABLE %I.%I ALTER CONSTRAINT %I NOT DEFERRABLE',
                       fk.schema_name, fk.table_name, fk.constraint_name);
    END LOOP;
END
$restore$;
"""


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
                select(func.count(ProductModel.id)).where(
                    ProductModel.product_image_url.is_not(None)
                ),
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
        (
            await session.execute(
                select(InventoryItem.serial_number).order_by(InventoryItem.serial_number),
            )
        )
        .scalars()
        .all()
    )
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
    *,
    exclude_fields: frozenset[str] | None = None,
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
        if exclude_fields and key in exclude_fields:
            continue
        if before_dict[key] != after_dict[key]:
            mismatches.append(f"{label}: expected {before_dict[key]!r}, got {after_dict[key]!r}")
    if list(before.serial_numbers) != list(after.serial_numbers):
        mismatches.append(
            f"Serial numbers differ: expected {len(before.serial_numbers)}, "
            f"got {len(after.serial_numbers)}",
        )
    return mismatches


RESTORE_OPERATION_COUNT_FIELDS = frozenset({"audit_log_count", "notification_count"})


def compare_restored_business_snapshots(
    before: BusinessSnapshot,
    after: BusinessSnapshot,
) -> list[str]:
    """Compare business data after restore; restore writes new audit/notification rows."""
    return compare_business_snapshots(
        before,
        after,
        exclude_fields=RESTORE_OPERATION_COUNT_FIELDS,
    )


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
