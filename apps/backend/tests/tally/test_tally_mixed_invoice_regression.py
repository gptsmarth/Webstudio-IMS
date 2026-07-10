"""Production-shaped mixed invoice: laptop + backpack + mouse."""

from __future__ import annotations

import gzip
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["auth.conftest"]

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    InventoryStatus,
    ProductCategory,
    SettingValueType,
    TallyLineOutcome,
    TallyProcessingStatus,
    tally_invoice_status_label,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
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


def _mixed_xml(*, guid: str, laptop_serial: str, mouse_serial: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>77001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>MIX/0001/26-27</VOUCHERNUMBER>
  <REFERENCE>MIX/0001/26-27</REFERENCE>
  <DATE>20260710</DATE>
  <PARTYLEDGERNAME>Mixed Buyer</PARTYLEDGERNAME>
  <LEDGERENTRIES.LIST><AMOUNT>-77500.00</AMOUNT></LEDGERENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS Vivobook 15 X1502ZA-EJ541WS</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>75000.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{laptop_serial}</BASICUSERDESCRIPTION>
      <BASICUSERDESCRIPTION>Warranty by ASUS</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>CARRY CASE ASUS BACKPACK</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>1000.00</AMOUNT>
  </ALLINVENTORYENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS MD100 Silent Wireless Mouse</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>1500.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{mouse_serial}</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


@pytest.mark.asyncio
async def test_mixed_laptop_backpack_mouse_invoice(
    db_session: AsyncSession,
    initialized_system,
    brand: Brand,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"MIX-{suffix}"
    laptop_serial = f"ABC123-{suffix}"
    mouse_serial = f"XYZ999-{suffix}"
    guid = f"mixed-guid-{suffix}"

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

    mouse_model = await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.MOUSE,
        model_number=f"MD100-{suffix}",
        model_name="ASUS MD100 Silent Wireless Mouse",
        actor=AuditActor.system(),
    )

    inventory = InventoryItemRepository(db_session)
    laptop = await inventory.create(
        serial_number=laptop_serial,
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    mouse = await inventory.create(
        serial_number=mouse_serial,
        product_model_id=mouse_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    xml = _mixed_xml(guid=guid, laptop_serial=laptop_serial, mouse_serial=mouse_serial)
    parsed = parse_vouchers_xml(xml)[0]
    assert parsed.inventory_lines[0].serial_number == laptop_serial
    assert parsed.inventory_lines[1].serial_number is None
    assert parsed.inventory_lines[2].serial_number == mouse_serial

    result = await TallySyncService(db_session).process_voucher_xml(
        xml,
        correlation_id="mixed-invoice",
        company_name=company,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 2

    await db_session.refresh(laptop)
    await db_session.refresh(mouse)
    assert laptop.status is InventoryStatus.SOLD
    assert mouse.status is InventoryStatus.SOLD

    sales = SaleRepository(db_session)
    laptop_sale = await sales.get_by_inventory_item_id(laptop.id)
    mouse_sale = await sales.get_by_inventory_item_id(mouse.id)
    assert laptop_sale is not None
    assert mouse_sale is not None
    assert laptop_sale.tally_voucher_guid == guid
    assert mouse_sale.tally_voucher_guid == guid
    assert laptop_sale.sale_amount == 75000.0
    assert mouse_sale.sale_amount == 1500.0
    assert laptop_sale.review_required is False
    assert mouse_sale.review_required is False
    assert laptop_sale.serial_source == "basicuserdescription"

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    invoice = await TallyProcessedInvoiceRepository(db_session).find_by_guid(company_sync.id, guid)
    assert invoice is not None
    assert invoice.processing_status is TallyProcessingStatus.SUCCESS
    assert tally_invoice_status_label(invoice.processing_status) == "processed"
    assert invoice.raw_xml_gzip is not None
    assert gzip.decompress(invoice.raw_xml_gzip).decode("utf-8").find(guid) >= 0
    assert invoice.grand_total is not None

    lines = await TallyProcessedInvoiceLineRepository(db_session).list_for_invoice(invoice.id)
    assert len(lines) == 3
    assert lines[0].line_outcome is TallyLineOutcome.SALE_APPLIED
    assert lines[1].line_outcome is TallyLineOutcome.ADDITIONAL_PRODUCT
    assert lines[1].is_additional_product is True
    assert lines[2].line_outcome is TallyLineOutcome.SALE_APPLIED


@pytest.mark.asyncio
async def test_empty_basicuserdescription_list_falls_back_to_serialnumber() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>empty-bud-guid</GUID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>1</VOUCHERNUMBER>
  <DATE>20260710</DATE>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>Item</STOCKITEMNAME>
    <BASICUSERDESCRIPTION.LIST></BASICUSERDESCRIPTION.LIST>
    <SERIALNUMBER>FALLBACK-SN-001</SERIALNUMBER>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""
    vouchers = parse_vouchers_xml(xml)
    assert vouchers[0].inventory_lines[0].serial_number == "FALLBACK-SN-001"
    assert vouchers[0].inventory_lines[0].serial_source == "serialnumber"
