"""Regression: AES/0147 backpack must never sell an unrelated laptop."""

from __future__ import annotations

import uuid

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
from webstudio_backend.integrations.tally.xml_parser import parse_vouchers_xml
from webstudio_backend.services.tally_sync_service import TallySyncService

# Production-shaped replay of AES/0147/26-27:
# Line 0 — laptop serial not in IMS
# Line 1 — backpack with NO serial (previously wrongly sold an ASUS laptop via fuzzy match)
AES_0147_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>93e8416c-3f92-4d33-aedf-7d6db428df93-00010b41</GUID>
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


@pytest.mark.asyncio
async def test_aes_0147_backpack_does_not_sell_unrelated_laptop(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    """P0 regression: backpack without serial must NOT deduct W1N0KD006934044."""
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    company_name = f"AES-0147-{uuid.uuid4().hex[:8]}"
    await settings.set_value(
        "tally_company_name",
        company_name,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )

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

    parsed = parse_vouchers_xml(AES_0147_XML)
    assert len(parsed) == 1
    assert parsed[0].inventory_lines[0].serial_number == "TBN0CX00904345A"
    assert parsed[0].inventory_lines[0].serial_source == "basicuserdescription"
    assert parsed[0].inventory_lines[1].serial_number is None

    result = await TallySyncService(db_session).process_voucher_xml(
        AES_0147_XML,
        correlation_id="aes-0147-regression",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 0

    await db_session.refresh(victim)
    assert victim.status is InventoryStatus.AVAILABLE

    sale = await SaleRepository(db_session).get_by_inventory_item_id(victim.id)
    assert sale is None

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company_name)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(
        company_sync.id,
        "93e8416c-3f92-4d33-aedf-7d6db428df93-00010b41",
    )
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.SUCCESS
    assert invoice.raw_xml_gzip is not None
    assert invoice.grand_total is not None

    lines = await TallyProcessedInvoiceLineRepository(db_session).list_for_invoice(invoice.id)
    assert len(lines) == 2
    assert lines[0].line_outcome is TallyLineOutcome.UNMATCHED_SERIALIZED_ITEM
    assert lines[0].is_unmatched_serialized is True
    assert lines[0].is_additional_product is False
    assert lines[0].normalized_serial == "TBN0CX00904345A"
    assert lines[1].line_outcome is TallyLineOutcome.ADDITIONAL_PRODUCT
    assert lines[1].is_additional_product is True
    assert lines[1].serial_number is None


@pytest.mark.asyncio
async def test_basicuserdescription_first_entry_is_serial_second_is_ignored() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>bud-priority-001</GUID>
  <MASTERID>1</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>1</VOUCHERNUMBER>
  <DATE>20260710</DATE>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ACER ASPIRE</STOCKITEMNAME>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>UN36FSI00B613004C20700</BASICUSERDESCRIPTION>
      <BASICUSERDESCRIPTION>Warranty by Acer Only</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""
    vouchers = parse_vouchers_xml(xml)
    assert vouchers[0].inventory_lines[0].serial_number == "UN36FSI00B613004C20700"
    assert vouchers[0].inventory_lines[0].normalized_serial == "UN36FSI00B613004C20700"
    assert "Warranty" not in (vouchers[0].inventory_lines[0].serial_number or "")
