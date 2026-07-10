"""Case D/E regression: duplicate IMS serial and already-sold serial."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["auth.conftest"]

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    SettingValueType,
    TallyLineOutcome,
    TallyProcessingStatus,
)
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
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
from webstudio_backend.services.tally_sync_service import TallySyncService


async def _enable_tally(db_session: AsyncSession, company_name: str) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    await settings.set_value(
        "tally_company_name",
        company_name,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )


def _voucher_xml(*, guid: str, serial: str, invoice: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>90001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{invoice}</VOUCHERNUMBER>
  <REFERENCE>{invoice}</REFERENCE>
  <DATE>20260710</DATE>
  <PARTYLEDGERNAME>Review Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS Test Model</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>1000.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{serial}</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


@pytest.mark.asyncio
async def test_case_d_duplicate_serial_in_ims_requires_review_no_sale(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company_name = f"CASE-D-{suffix}"
    serial = f"DUP-SERIAL-{suffix}"
    await _enable_tally(db_session, company_name)

    inventory = InventoryItemRepository(db_session)
    first = await inventory.create(
        serial_number=serial,
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    # Bypass repository uniqueness to simulate corrupt case-variant duplicate rows.
    second = InventoryItem(
        serial_number=f"{serial}-TMP",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    db_session.add(second)
    await db_session.flush()
    await db_session.execute(
        text("UPDATE webstudio.inventory_items SET serial_number = :s WHERE id = :id"),
        {"s": serial.lower(), "id": second.id},
    )
    await db_session.commit()
    await db_session.refresh(second)

    guid = f"case-d-guid-{suffix}"
    result = await TallySyncService(db_session).process_voucher_xml(
        _voucher_xml(guid=guid, serial=serial, invoice=f"INV-D-{suffix}"),
        correlation_id="case-d",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 0

    await db_session.refresh(first)
    await db_session.refresh(second)
    assert first.status is InventoryStatus.AVAILABLE
    assert second.status is InventoryStatus.AVAILABLE

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company_name)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(company_sync.id, guid)
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED
    assert invoice.review_required is True

    lines = await TallyProcessedInvoiceLineRepository(db_session).list_for_invoice(invoice.id)
    assert len(lines) == 1
    assert lines[0].line_outcome is TallyLineOutcome.REVIEW_REQUIRED_DUPLICATE_SERIAL
    assert lines[0].review_required is True


@pytest.mark.asyncio
async def test_case_e_already_sold_serial_requires_review_no_duplicate_sale(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company_name = f"CASE-E-{suffix}"
    serial = f"SOLD-SERIAL-{suffix}"
    await _enable_tally(db_session, company_name)

    inventory = InventoryItemRepository(db_session)
    item = await inventory.create(
        serial_number=serial,
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.SOLD,
    )
    await db_session.commit()

    guid = f"case-e-guid-{suffix}"
    result = await TallySyncService(db_session).process_voucher_xml(
        _voucher_xml(guid=guid, serial=serial, invoice=f"INV-E-{suffix}"),
        correlation_id="case-e",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 0
    assert result.counters.duplicates == 1

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD
    assert await SaleRepository(db_session).get_by_inventory_item_id(item.id) is None

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company_name)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(company_sync.id, guid)
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.COMPLETED_WITH_REVIEW_REQUIRED

    lines = await TallyProcessedInvoiceLineRepository(db_session).list_for_invoice(invoice.id)
    assert lines[0].line_outcome is TallyLineOutcome.REVIEW_REQUIRED_ALREADY_SOLD
    assert lines[0].review_required is True
