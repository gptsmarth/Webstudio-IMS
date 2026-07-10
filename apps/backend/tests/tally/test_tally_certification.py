"""Certification tests: crash rollback, restart resume, GUID idempotency."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["auth.conftest"]

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    SettingValueType,
    TallyLineOutcome,
    TallyProcessingStatus,
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
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.integrations.tally.incremental_sync import resolve_incremental_from_date
from webstudio_backend.services.tally_sync_service import TallySyncService

AES_0147_GUID = "93e8416c-3f92-4d33-aedf-7d6db428df93-00010b41"


def _aes0147_xml(guid: str = AES_0147_GUID) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>68417</MASTERID>
  <VOUCHERTYPENAME>NEW SALE</VOUCHERTYPENAME>
  <VOUCHERNUMBER>AES/0147/26-27</VOUCHERNUMBER>
  <REFERENCE>AES/0147/26-27</REFERENCE>
  <DATE>20260602</DATE>
  <PARTYLEDGERNAME>CHANDER BAWA</PARTYLEDGERNAME>
  <NARRATION>9729511915 cash</NARRATION>
  <LEDGERENTRIES.LIST><AMOUNT>-76000.00</AMOUNT></LEDGERENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS X1407CA-LY1581WS</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>75000.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>TBN0CX00904345A</BASICUSERDESCRIPTION>
      <BASICUSERDESCRIPTION>Warranty by ASUS</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>CARRY CASE ASUS BACKPACK</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>1000.00</AMOUNT>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>
"""


AES_0147_XML = _aes0147_xml()


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


def _sale_xml(*, guid: str, serial: str, invoice: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>91001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{invoice}</VOUCHERNUMBER>
  <REFERENCE>{invoice}</REFERENCE>
  <DATE>20260710</DATE>
  <PARTYLEDGERNAME>Cert Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS Cert Model</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>50000.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{serial}</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


@pytest.mark.asyncio
async def test_crash_during_processing_rolls_back_inventory_and_sale(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    """Simulated mid-voucher crash must not leave partial inventory deduction."""
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"CERT-CRASH-{suffix}"
    serial = f"CRASH-SN-{suffix}"
    guid = f"crash-guid-{suffix}"
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

    service = TallySyncService(db_session)
    with patch.object(
        service._recorder,
        "record_inventory_status_change",
        new=AsyncMock(side_effect=RuntimeError("simulated crash after sale create")),
    ):
        result = await service.process_voucher_xml(
            _sale_xml(guid=guid, serial=serial, invoice=f"CRASH-{suffix}"),
            correlation_id="crash-cert",
            company_name=company,
        )
    await db_session.commit()

    assert result.success is False
    await db_session.refresh(item)
    assert item.status is InventoryStatus.AVAILABLE
    assert await SaleRepository(db_session).get_by_inventory_item_id(item.id) is None

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(company_sync.id, guid)
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.FAILED


@pytest.mark.asyncio
async def test_same_guid_cannot_create_two_sales_or_deduct_twice(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"CERT-IDEM-{suffix}"
    serial = f"IDEM-SN-{suffix}"
    guid = f"idem-guid-{suffix}"
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

    xml = _sale_xml(guid=guid, serial=serial, invoice=f"IDEM-{suffix}")
    service = TallySyncService(db_session)

    first = await service.process_voucher_xml(xml, correlation_id="idem-1", company_name=company)
    await db_session.commit()
    assert first.success is True
    assert first.counters.sales_created == 1

    second = await service.process_voucher_xml(xml, correlation_id="idem-2", company_name=company)
    await db_session.commit()
    assert second.counters.invoices_skipped >= 1
    assert second.counters.sales_created == 0

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD
    sale = await SaleRepository(db_session).get_by_inventory_item_id(item.id)
    assert sale is not None
    assert sale.tally_voucher_guid == guid


def test_overnight_restart_resumes_from_last_imported_voucher_date() -> None:
    """Server shutdown overnight → morning resume window starts at last imported date."""
    company = type("CS", (), {})()
    company.last_imported_voucher_date = date(2026, 7, 9)
    company.last_successful_sync_at = datetime(2026, 7, 9, 18, 30, tzinfo=UTC)
    from_date = resolve_incremental_from_date(company, today=date(2026, 7, 10))
    assert from_date == date(2026, 7, 9)
    assert from_date <= date(2026, 7, 10)
    assert (date(2026, 7, 10) - from_date) == timedelta(days=1)


@pytest.mark.asyncio
async def test_aes0147_replay_then_reimport_skips_without_selling_laptop(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    company = f"CERT-AES-{uuid.uuid4().hex[:8]}"
    await _enable(db_session, company)
    guid = f"aes-cert-{uuid.uuid4().hex}"
    xml = _aes0147_xml(guid=guid)

    inventory = InventoryItemRepository(db_session)
    existing = await inventory.find_by_serial_number("W1N0KD006934044")
    if existing is not None:
        existing.status = InventoryStatus.AVAILABLE
        existing.product_model_id = product_model.id
        existing.current_location_id = location.id
        await db_session.flush()
        victim = existing
    else:
        victim = await inventory.create(
            serial_number="W1N0KD006934044",
            product_model_id=product_model.id,
            color="Black",
            current_location_id=location.id,
            status=InventoryStatus.AVAILABLE,
        )
    await db_session.commit()

    service = TallySyncService(db_session)
    first = await service.process_voucher_xml(
        xml, correlation_id="aes-cert-1", company_name=company
    )
    await db_session.commit()
    assert first.success is True
    assert first.counters.sales_created == 0

    second = await service.process_voucher_xml(
        xml, correlation_id="aes-cert-2", company_name=company
    )
    await db_session.commit()
    assert second.counters.invoices_skipped >= 1
    assert second.counters.sales_created == 0

    await db_session.refresh(victim)
    assert victim.status is InventoryStatus.AVAILABLE
    assert await SaleRepository(db_session).get_by_inventory_item_id(victim.id) is None

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(
        company_sync.id,
        guid,
    )
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.SUCCESS
    lines = await TallyProcessedInvoiceLineRepository(db_session).list_for_invoice(invoice.id)
    assert all(
        line.line_outcome
        in {
            TallyLineOutcome.ADDITIONAL_PRODUCT,
            TallyLineOutcome.UNMATCHED_SERIALIZED_ITEM,
        }
        for line in lines
    )
