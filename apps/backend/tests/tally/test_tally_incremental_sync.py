"""Enterprise incremental Tally synchronization tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import InventoryStatus, SettingValueType, TallyProcessingStatus
from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.infrastructure.repositories.inventory_item_repository import InventoryItemRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import TallyCompanySyncRepository
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import TallyProcessedInvoiceRepository
from webstudio_backend.integrations.tally.incremental_sync import (
    SYNC_INTERVAL_MAX_SECONDS,
    SYNC_INTERVAL_MIN_SECONDS,
    clamp_sync_interval_seconds,
    resolve_incremental_from_date,
)
from webstudio_backend.integrations.tally.xml_parser import parse_vouchers_xml
from webstudio_backend.services.tally_sync_service import TallySyncService
from tests.tally.fixtures.sample_vouchers import SAMPLE_VOUCHER_XML


def test_clamp_sync_interval_seconds() -> None:
    assert clamp_sync_interval_seconds(30) == SYNC_INTERVAL_MIN_SECONDS
    assert clamp_sync_interval_seconds(300) == 300
    assert clamp_sync_interval_seconds(99999) == SYNC_INTERVAL_MAX_SECONDS


def test_resolve_incremental_from_date_uses_last_successful_sync() -> None:
    sync_at = datetime(2026, 6, 27, 15, 30, tzinfo=UTC)
    company = TallyCompanySync(company_name="WEBSTUDIO")
    company.last_successful_sync_at = sync_at
    assert resolve_incremental_from_date(company, today=date(2026, 7, 2)) == date(2026, 6, 27)


def test_resolve_incremental_from_date_first_sync_uses_today() -> None:
    company = TallyCompanySync(company_name="WEBSTUDIO")
    today = date(2026, 7, 2)
    assert resolve_incremental_from_date(company, today=today) == today


def test_parse_voucher_amount() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
      <GUID>amount-guid</GUID>
      <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
      <VOUCHERNUMBER>99</VOUCHERNUMBER>
      <DATE>20260627</DATE>
      <PARTYLEDGERNAME>Customer A</PARTYLEDGERNAME>
      <LEDGERENTRIES.LIST><AMOUNT>-45000.00</AMOUNT></LEDGERENTRIES.LIST>
      <ALLINVENTORYENTRIES.LIST>
        <STOCKITEMNAME>Test Item</STOCKITEMNAME>
        <ACTUALQTY>1</ACTUALQTY>
      </ALLINVENTORYENTRIES.LIST>
    </VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""
    vouchers = parse_vouchers_xml(xml)
    assert len(vouchers) == 1
    assert vouchers[0].amount == "45000.00"


@pytest.mark.asyncio
async def test_guid_duplicate_skipped_on_second_import(db_session: AsyncSession) -> None:
    repo = TallyProcessedInvoiceRepository(db_session)
    company_sync = await TallyCompanySyncRepository(db_session).get_or_create("WEBSTUDIO")
    vouchers = parse_vouchers_xml(SAMPLE_VOUCHER_XML)
    voucher = vouchers[0]

    await repo.get_or_create_pending(
        company_sync_id=company_sync.id,
        guid=voucher.guid,
        master_id=voucher.master_id,
        voucher_number=voucher.voucher_number,
        printed_invoice_number=voucher.printed_invoice_number,
        voucher_type=voucher.voucher_type,
        voucher_date=voucher.voucher_date,
        party_name=voucher.party_name,
        amount=voucher.amount,
    )
    invoice = await repo.find_by_guid(company_sync.id, voucher.guid)
    assert invoice is not None
    await repo.update_status(invoice, TallyProcessingStatus.SUCCESS)
    await db_session.commit()

    service = TallySyncService(db_session)
    assert await service._should_skip_voucher(company_sync.id, voucher) is True


@pytest.mark.asyncio
async def test_fallback_fingerprint_duplicate_skipped(db_session: AsyncSession) -> None:
    repo = TallyProcessedInvoiceRepository(db_session)
    company_sync = await TallyCompanySyncRepository(db_session).get_or_create("WEBSTUDIO")

    await repo.get_or_create_pending(
        company_sync_id=company_sync.id,
        guid="original-guid",
        master_id="1",
        voucher_number="42",
        printed_invoice_number="WEB/24-25/00042",
        voucher_type="Sales",
        voucher_date=date(2024, 6, 15),
        party_name="Walk-in Customer",
        amount="125000.00",
    )
    invoice = await repo.find_by_guid(company_sync.id, "original-guid")
    assert invoice is not None
    await repo.update_status(invoice, TallyProcessingStatus.SUCCESS)
    await db_session.commit()

    vouchers = parse_vouchers_xml(SAMPLE_VOUCHER_XML)
    changed_guid = vouchers[0]
    assert changed_guid.guid != "original-guid"

    duplicate = await repo.find_by_fallback_fingerprint(
        company_sync.id,
        voucher_date=date(2024, 6, 15),
        voucher_number="42",
        amount="125000.00",
        party_name="Walk-in Customer",
    )
    assert duplicate is not None

    service = TallySyncService(db_session)
    changed_guid_voucher = type(changed_guid)(
        guid="new-guid-after-tally-change",
        master_id=changed_guid.master_id,
        voucher_type=changed_guid.voucher_type,
        voucher_number="42",
        printed_invoice_number=changed_guid.printed_invoice_number,
        voucher_date=date(2024, 6, 15),
        party_name="Walk-in Customer",
        narration=changed_guid.narration,
        inventory_lines=changed_guid.inventory_lines,
        payment_mode=changed_guid.payment_mode,
        amount="125000.00",
    )
    assert await service._should_skip_voucher(company_sync.id, changed_guid_voucher) is True


@pytest.mark.asyncio
async def test_process_voucher_xml_skips_already_imported(db_session: AsyncSession) -> None:
    from webstudio_backend.infrastructure.repositories import BrandRepository, LocationRepository, ProductModelRepository
    from webstudio_backend.infrastructure.database.enums import LocationType, StorageType, StorageUnit

    suffix = uuid.uuid4().hex[:8]

    dedup_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
      <GUID>dedup-guid-{suffix}</GUID>
      <MASTERID>90001</MASTERID>
      <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
      <VOUCHERNUMBER>{suffix}-9001</VOUCHERNUMBER>
      <REFERENCE>WEB/26-27/09001</REFERENCE>
      <DATE>20260701</DATE>
      <PARTYLEDGERNAME>Dedup Customer</PARTYLEDGERNAME>
      <ALLINVENTORYENTRIES.LIST>
        <STOCKITEMNAME>ASUS Vivobook X1502ZA</STOCKITEMNAME>
        <ACTUALQTY>1 Nos</ACTUALQTY>
        <BATCHALLOCATIONS.LIST>
          <SERIALNUMBER>SN-INCR-{suffix}</SERIALNUMBER>
        </BATCHALLOCATIONS.LIST>
      </ALLINVENTORYENTRIES.LIST>
    </VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""

    brand = await BrandRepository(db_session).create(f"INCR-SYNC-{suffix}")
    location = await LocationRepository(db_session).create(
        f"INCR-SYNC-LOC-{suffix}",
        location_type=LocationType.WAREHOUSE,
    )
    product_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number=f"X1502ZA-{suffix}",
        model_name="Vivobook 15",
        cpu="Intel Core i5-1235U",
        ram_gb=16,
        storage_value=512,
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )

    settings = SystemSettingRepository(db_session)
    await settings.set_value("tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=None)
    await settings.set_value(
        "tally_company_name",
        "WEBSTUDIO",
        value_type=SettingValueType.STRING,
        updated_by_user_id=None,
    )

    inventory_repo = InventoryItemRepository(db_session)
    await inventory_repo.create(
        serial_number=f"SN-INCR-{suffix}",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    service = TallySyncService(db_session)
    first = await service.process_voucher_xml(dedup_xml, correlation_id="first", company_name="WEBSTUDIO")
    await db_session.commit()
    assert first.counters.invoices_imported >= 1

    second = await service.process_voucher_xml(dedup_xml, correlation_id="second", company_name="WEBSTUDIO")
    assert second.counters.invoices_skipped >= 1
    assert second.counters.invoices_imported == 0


@pytest.mark.asyncio
async def test_offline_gap_uses_last_successful_sync_date(db_session: AsyncSession) -> None:
    company_sync = await TallyCompanySyncRepository(db_session).get_or_create("WEBSTUDIO")
    friday = datetime(2026, 6, 27, 18, 0, tzinfo=UTC)
    company_sync.last_successful_sync_at = friday
    await db_session.commit()

    from_date = resolve_incremental_from_date(company_sync, today=date(2026, 7, 2))
    assert from_date == date(2026, 6, 27)
    assert from_date <= date(2026, 7, 2)
    assert (date(2026, 7, 2) - from_date) == timedelta(days=5)
