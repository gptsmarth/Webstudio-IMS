"""Disaster recovery integration test — full business-state backup and restore."""

from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    SettingValueType,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.services.backup_completeness import (
    collect_business_snapshot,
    compare_restored_business_snapshots,
    truncate_webstudio_data,
)
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.sale_service import SaleService

pytest_plugins = ["auth.conftest"]

pytestmark = pytest.mark.skipif(
    shutil.which("pg_dump") is None or shutil.which("psql") is None,
    reason="pg_dump and psql are required for disaster recovery integration test",
)


@pytest_asyncio.fixture(autouse=True)
async def disaster_recovery_isolated_db(db_session: AsyncSession) -> None:
    """Each DR test starts from an empty webstudio schema (shared CI database)."""
    await truncate_webstudio_data(db_session)
    db_session.expire_all()


@pytest_asyncio.fixture
async def disaster_recovery_backup_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> object:
    monkeypatch.setenv("WEBSTUDIO_BACKUP_REAL_DUMP", "1")
    return tmp_path


async def _seed_representative_business_data(db_session: AsyncSession) -> AuditActor:
    settings_repo = SystemSettingRepository(db_session)
    await settings_repo.set_value(
        "tally_enabled",
        "true",
        value_type=SettingValueType.BOOLEAN,
    )
    await settings_repo.set_value(
        "tally_company_name",
        "DR Test Company",
        value_type=SettingValueType.STRING,
    )
    await settings_repo.set_value(
        "gemini_model",
        "gemini-2.5-flash",
        value_type=SettingValueType.STRING,
    )

    brand = await BrandRepository(db_session).create("Dell")
    location = await LocationRepository(db_session).create(
        "Main Store",
        location_type=LocationType.WAREHOUSE,
    )
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="DR-7420",
        model_name="Latitude 7420",
        cpu="Intel Core i7",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
        product_image_url="https://example.com/laptop.jpg",
    )
    inventory_repo = InventoryItemRepository(db_session)
    item = await inventory_repo.create(
        serial_number="SN-DR-001",
        product_model_id=product_model.id,
        color="Silver",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
        purchase_date=date(2026, 1, 10),
    )
    main_admin = await UserRepository(db_session).get_main_admin()
    assert main_admin is not None
    actor = AuditActor(
        user_id=main_admin.id,
        display_name=main_admin.display_name,
        role=main_admin.role.value,
    )
    await SaleService(db_session).reflect_manual_sale(
        item.id,
        invoice_number="INV-DR-001",
        customer_name="Acme Retail",
        payment_mode="UPI",
        sale_date=date(2026, 2, 1),
        remarks="Disaster recovery validation sale",
        actor=actor,
    )
    await db_session.commit()
    return actor


@pytest.mark.asyncio
async def test_disaster_recovery_full_business_state(
    db_session: AsyncSession,
    test_settings: Settings,
    initialized_system,
    disaster_recovery_backup_dir,
) -> None:
    await _seed_representative_business_data(db_session)
    settings_repo = SystemSettingRepository(db_session)
    before = await collect_business_snapshot(db_session, settings_repo)
    assert before.inventory_count >= 1
    assert before.sales_count >= 1
    assert before.brands_count >= 1
    assert before.locations_count >= 1
    assert before.product_models_count >= 1
    assert before.tally_company_name == "DR Test Company"

    backup_engine = BackupEngine(
        db_session,
        test_settings,
        backup_dir=disaster_recovery_backup_dir,
    )
    created = await backup_engine.create_backup(trigger_type="manual")
    manifest = backup_engine.read_manifest_from_archive(
        disaster_recovery_backup_dir / created.filename,
    )
    assert manifest.get("backup_version") == "2.1"
    assert manifest.get("database_dump_mode") == "data_only"
    assert manifest.get("notification_count") is not None
    assert manifest.get("product_image_count") is not None

    restore_engine = RestoreEngine(
        db_session,
        test_settings,
        backup_dir=disaster_recovery_backup_dir,
    )
    result = await restore_engine.execute_restore(
        filename=created.filename,
        restore_scope="entire_database",
        create_emergency_backup=False,
        confirmed=True,
    )
    assert result.success is True
    assert result.verification_status in {"success", "warning"}

    db_session.expire_all()
    after = await collect_business_snapshot(db_session, settings_repo)
    mismatches = compare_restored_business_snapshots(before, after)
    assert mismatches == [], f"Business state mismatch after restore: {mismatches}"


@pytest.mark.asyncio
async def test_disaster_recovery_clean_database_restore(
    db_session: AsyncSession,
    test_settings: Settings,
    initialized_system,
    disaster_recovery_backup_dir,
) -> None:
    await _seed_representative_business_data(db_session)
    settings_repo = SystemSettingRepository(db_session)
    before = await collect_business_snapshot(db_session, settings_repo)

    backup_engine = BackupEngine(
        db_session,
        test_settings,
        backup_dir=disaster_recovery_backup_dir,
    )
    created = await backup_engine.create_backup(trigger_type="manual")

    await truncate_webstudio_data(db_session)
    db_session.expire_all()

    restore_engine = RestoreEngine(
        db_session,
        test_settings,
        backup_dir=disaster_recovery_backup_dir,
    )
    result = await restore_engine.execute_restore(
        filename=created.filename,
        restore_scope="entire_database",
        create_emergency_backup=False,
        confirmed=True,
    )
    assert result.success is True

    db_session.expire_all()
    after = await collect_business_snapshot(db_session, settings_repo)
    mismatches = compare_restored_business_snapshots(before, after)
    assert mismatches == [], f"Clean-database restore mismatch: {mismatches}"
