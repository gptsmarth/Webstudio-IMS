"""GUID watermark optimization — incremental sync efficiency tests."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["auth.conftest"]

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    SettingValueType,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.sale_repository import SaleRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.infrastructure.repositories.tally_company_sync_repository import (
    TallyCompanySyncRepository,
)
from webstudio_backend.integrations.tally.incremental_sync import (
    partition_by_guid_watermark,
    resolve_incremental_from_date,
)
from webstudio_backend.integrations.tally.types import TallyVoucher
from webstudio_backend.services.tally_sync_service import TallySyncService


def _voucher(
    *,
    guid: str,
    voucher_date: date,
    voucher_type: str = "Sales",
    invoice: str = "INV-1",
    master_id: str = "1",
) -> TallyVoucher:
    return TallyVoucher(
        guid=guid,
        master_id=master_id,
        voucher_type=voucher_type,
        voucher_number=invoice,
        printed_invoice_number=invoice,
        voucher_date=voucher_date,
        party_name="Buyer",
        narration=None,
        inventory_lines=[],
    )


def _envelope(vouchers_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<ENVELOPE><BODY><DATA><TALLYMESSAGE>{vouchers_xml}"
        "</TALLYMESSAGE></DATA></BODY></ENVELOPE>"
    )


def _accessory_voucher_xml(
    *,
    guid: str,
    voucher_type: str,
    invoice: str,
    master_id: str,
    voucher_date: str = "20260710",
) -> str:
    return f"""<VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>{master_id}</MASTERID>
  <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{invoice}</VOUCHERNUMBER>
  <REFERENCE>{invoice}</REFERENCE>
  <DATE>{voucher_date}</DATE>
  <PARTYLEDGERNAME>Watermark Buyer</PARTYLEDGERNAME>
  <LEDGERENTRIES.LIST><AMOUNT>-1000.00</AMOUNT></LEDGERENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>CARRY CASE ACCESSORY</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>1000.00</AMOUNT>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER>"""


def _sale_voucher_xml(
    *,
    guid: str,
    serial: str,
    invoice: str,
    voucher_type: str = "Sales",
    master_id: str = "91001",
    voucher_date: str = "20260710",
) -> str:
    return f"""<VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>{master_id}</MASTERID>
  <VOUCHERTYPENAME>{voucher_type}</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{invoice}</VOUCHERNUMBER>
  <REFERENCE>{invoice}</REFERENCE>
  <DATE>{voucher_date}</DATE>
  <PARTYLEDGERNAME>Watermark Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS Cert Model</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>50000.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{serial}</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER>"""


async def _enable(db_session: AsyncSession, company: str) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    await settings.set_value(
        "tally_company_name",
        company,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )


def test_partition_by_guid_watermark_skips_historical_efficiently() -> None:
    """Scenario 2 unit: 300 historical vouchers skipped after watermark GUID."""
    day = date(2026, 7, 10)
    historical = [
        _voucher(guid=f"hist-{index:04d}", voucher_date=day, invoice=f"H-{index}")
        for index in range(300)
    ]
    new_vouchers = [
        _voucher(guid="new-0001", voucher_date=day, invoice="N-1"),
        _voucher(guid="new-0002", voucher_date=day, invoice="N-2"),
    ]
    all_vouchers = [*historical, *new_vouchers]
    partition = partition_by_guid_watermark(all_vouchers, "hist-0299")
    assert partition.watermark_found is True
    assert partition.historical_skipped == 300
    assert [voucher.guid for voucher in partition.to_process] == ["new-0001", "new-0002"]


def test_partition_by_guid_watermark_missing_guid_processes_all() -> None:
    day = date(2026, 7, 10)
    vouchers = [_voucher(guid=f"g-{index}", voucher_date=day) for index in range(5)]
    partition = partition_by_guid_watermark(vouchers, "missing-guid")
    assert partition.watermark_found is False
    assert partition.historical_skipped == 0
    assert len(partition.to_process) == 5


def test_partition_by_guid_watermark_works_across_voucher_types() -> None:
    day = date(2026, 7, 10)
    vouchers = [
        _voucher(guid="sales-1", voucher_date=day, voucher_type="Sales"),
        _voucher(guid="newsale-1", voucher_date=day, voucher_type="NEW SALE"),
        _voucher(guid="sales-2", voucher_date=day, voucher_type="Sales"),
    ]
    partition = partition_by_guid_watermark(vouchers, "newsale-1")
    assert partition.historical_skipped == 2
    assert [voucher.guid for voucher in partition.to_process] == ["sales-2"]


@pytest.mark.asyncio
async def test_scenario1_overnight_restart_imports_only_new_guids(
    db_session: AsyncSession,
    initialized_system,
) -> None:
    """Server OFF overnight; Sales + NEW SALE created; restart imports only new GUIDs."""
    suffix = uuid.uuid4().hex[:8]
    company = f"WM-OVERNIGHT-{suffix}"
    await _enable(db_session, company)

    evening_xml = _envelope(
        _accessory_voucher_xml(
            guid=f"eve-sales-{suffix}",
            voucher_type="Sales",
            invoice=f"WEB/EVE/{suffix}",
            master_id="1001",
            voucher_date="20260709",
        )
        + _accessory_voucher_xml(
            guid=f"eve-newsale-{suffix}",
            voucher_type="NEW SALE",
            invoice=f"AES/EVE/{suffix}",
            master_id="1002",
            voucher_date="20260709",
        )
    )
    service = TallySyncService(db_session)
    evening = await service.process_voucher_xml(
        evening_xml, correlation_id="eve-1", company_name=company
    )
    await db_session.commit()
    assert evening.success is True
    assert evening.counters.invoices_imported == 2

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    assert company_sync.last_processed_guid == f"eve-sales-{suffix}"
    assert company_sync.last_imported_voucher_date == date(2026, 7, 9)
    assert company_sync.last_processed_voucher_type in {"Sales", "NEW SALE"}
    assert company_sync.last_processed_invoice_number is not None

    from_date = resolve_incremental_from_date(company_sync, today=date(2026, 7, 10))
    assert from_date == date(2026, 7, 9)

    morning_xml = _envelope(
        _accessory_voucher_xml(
            guid=f"eve-sales-{suffix}",
            voucher_type="Sales",
            invoice=f"WEB/EVE/{suffix}",
            master_id="1001",
            voucher_date="20260709",
        )
        + _accessory_voucher_xml(
            guid=f"eve-newsale-{suffix}",
            voucher_type="NEW SALE",
            invoice=f"AES/EVE/{suffix}",
            master_id="1002",
            voucher_date="20260709",
        )
        + _accessory_voucher_xml(
            guid=f"morn-sales-{suffix}",
            voucher_type="Sales",
            invoice=f"WEB/MORN/{suffix}",
            master_id="2001",
            voucher_date="20260710",
        )
        + _accessory_voucher_xml(
            guid=f"morn-newsale-{suffix}",
            voucher_type="NEW SALE",
            invoice=f"AES/MORN/{suffix}",
            master_id="2002",
            voucher_date="20260710",
        )
    )
    morning = await service.process_voucher_xml(
        morning_xml, correlation_id="morn-1", company_name=company
    )
    await db_session.commit()
    assert morning.counters.watermark_skipped == 2
    assert morning.counters.invoices_imported == 2
    assert morning.counters.vouchers_processed == 2

    await db_session.refresh(company_sync)
    assert company_sync.last_processed_guid == f"morn-sales-{suffix}"
    assert company_sync.last_imported_voucher_date == date(2026, 7, 10)


@pytest.mark.asyncio
async def test_scenario2_daybook_watermark_skips_full_processing(
    db_session: AsyncSession,
    initialized_system,
) -> None:
    """300 historical vouchers in Day Book; only post-watermark vouchers fully processed."""
    suffix = uuid.uuid4().hex[:8]
    company = f"WM-HIST-{suffix}"
    await _enable(db_session, company)

    historical_parts = [
        _accessory_voucher_xml(
            guid=f"hist-{index:04d}-{suffix}",
            voucher_type="Sales" if index % 2 == 0 else "NEW SALE",
            invoice=f"H/{index:04d}/{suffix}",
            master_id=str(10000 + index),
        )
        for index in range(300)
    ]
    mock_stats = {
        "total": 1,
        "completed": 1,
        "failed": 0,
        "sales": 0,
        "duplicates": 0,
        "missing_serial": 1,
        "missing_model": 0,
        "model_mismatches": 0,
        "ignored": 0,
        "review_required": 0,
    }
    service = TallySyncService(db_session)
    with patch.object(service, "_process_voucher", new=AsyncMock(return_value=mock_stats)):
        seed = await service.process_voucher_xml(
            _envelope("".join(historical_parts)),
            correlation_id="seed",
            company_name=company,
        )
    await db_session.commit()
    assert seed.counters.invoices_imported == 300

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    assert company_sync.last_processed_guid == f"hist-0299-{suffix}"

    new_parts = [
        _accessory_voucher_xml(
            guid=f"new-0001-{suffix}",
            voucher_type="Sales",
            invoice=f"N/0001/{suffix}",
            master_id="30001",
        ),
        _accessory_voucher_xml(
            guid=f"new-0002-{suffix}",
            voucher_type="NEW SALE",
            invoice=f"N/0002/{suffix}",
            master_id="30002",
        ),
    ]
    daybook = _envelope("".join(historical_parts) + "".join(new_parts))
    with patch.object(
        service,
        "_process_voucher",
        new=AsyncMock(return_value=mock_stats),
    ) as process_mock:
        result = await service.process_voucher_xml(
            daybook, correlation_id="daybook", company_name=company
        )
    await db_session.commit()

    assert result.counters.watermark_skipped == 300
    assert process_mock.await_count == 2
    assert result.counters.invoices_imported == 2


@pytest.mark.asyncio
async def test_scenario3_duplicate_scheduler_no_double_inventory(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    """Duplicate scheduler execution must not double-sell or double-deduct."""
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"WM-DUP-{suffix}"
    serial = f"WM-DUP-SN-{suffix}"
    guid = f"dup-guid-{suffix}"
    await _enable(db_session, company)

    inventory = InventoryItemRepository(db_session)
    item = await inventory.create(
        serial_number=serial,
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    xml = _envelope(
        _sale_voucher_xml(
            guid=guid,
            serial=serial,
            invoice=f"DUP/{suffix}",
            voucher_type="Sales",
        )
    )
    service = TallySyncService(db_session)
    first = await service.process_voucher_xml(xml, correlation_id="dup-1", company_name=company)
    await db_session.commit()
    second = await service.process_voucher_xml(xml, correlation_id="dup-2", company_name=company)
    await db_session.commit()

    assert first.counters.sales_created == 1
    assert second.counters.invoices_skipped >= 1
    assert second.counters.sales_created == 0
    assert second.counters.vouchers_processed == 0

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD
    sale = await SaleRepository(db_session).get_by_inventory_item_id(item.id)
    assert sale is not None
    assert sale.tally_voucher_guid == guid


@pytest.mark.asyncio
async def test_scenario4_power_failure_watermark_resumes_without_skip(
    db_session: AsyncSession,
    initialized_system,
) -> None:
    """Power failure mid-day: watermark resumes; no invoice skipped or duplicated."""
    suffix = uuid.uuid4().hex[:8]
    company = f"WM-PWR-{suffix}"
    await _enable(db_session, company)

    first_xml = _envelope(
        _accessory_voucher_xml(
            guid=f"pwr-1-{suffix}",
            voucher_type="Sales",
            invoice=f"PWR/1/{suffix}",
            master_id="4001",
        )
    )
    service = TallySyncService(db_session)
    first = await service.process_voucher_xml(
        first_xml, correlation_id="pwr-1", company_name=company
    )
    await db_session.commit()
    assert first.counters.invoices_imported == 1

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    assert company_sync.last_processed_guid == f"pwr-1-{suffix}"
    # Simulate crash before later vouchers were processed: watermark stays at pwr-1.
    company_sync.last_successful_sync_at = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    await db_session.commit()

    resume_xml = _envelope(
        _accessory_voucher_xml(
            guid=f"pwr-1-{suffix}",
            voucher_type="Sales",
            invoice=f"PWR/1/{suffix}",
            master_id="4001",
        )
        + _accessory_voucher_xml(
            guid=f"pwr-2-{suffix}",
            voucher_type="NEW SALE",
            invoice=f"PWR/2/{suffix}",
            master_id="4002",
        )
        + _accessory_voucher_xml(
            guid=f"pwr-3-{suffix}",
            voucher_type="Sales",
            invoice=f"PWR/3/{suffix}",
            master_id="4003",
        )
    )
    resume = await service.process_voucher_xml(
        resume_xml, correlation_id="pwr-resume", company_name=company
    )
    await db_session.commit()

    assert resume.counters.watermark_skipped == 1
    assert resume.counters.invoices_imported == 2
    assert resume.counters.vouchers_processed == 2

    await db_session.refresh(company_sync)
    assert company_sync.last_processed_guid == f"pwr-3-{suffix}"
    assert company_sync.last_processed_voucher_type == "Sales"
    assert company_sync.last_processed_invoice_number == f"PWR/3/{suffix}"

    # Re-run must not re-import.
    again = await service.process_voucher_xml(
        resume_xml, correlation_id="pwr-again", company_name=company
    )
    assert again.counters.invoices_imported == 0
    assert again.counters.vouchers_processed == 0
