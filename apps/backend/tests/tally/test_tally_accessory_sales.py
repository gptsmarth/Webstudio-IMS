"""Tally sync tests for accessories and mixed laptop+accessory invoices."""

from __future__ import annotations

import uuid

import pytest

pytest_plugins = ["auth.conftest"]
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    AccessoryKind,
    InventoryStatus,
    ProductCategory,
    SettingValueType,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
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
from webstudio_backend.integrations.tally.xml_parser import (
    expand_inventory_lines,
    parse_vouchers_xml,
)
from webstudio_backend.services.tally_sync_service import TallySyncService


async def _ensure_accessory_model(db_session: AsyncSession, brand: Brand) -> ProductModel:
    repo = ProductModelRepository(db_session)
    for existing in await repo.list_all_for_brand(brand.id):
        if existing.model_number.lower() == "md100":
            return existing
    return await repo.create(
        brand_id=brand.id,
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.MOUSE,
        part_number="90NB0X02-M0A010",
        model_number="MD100",
        model_name="ASUS MD100 Silent Wireless Mouse",
        actor=AuditActor.system(),
    )


async def _ensure_available_item(
    db_session: AsyncSession,
    *,
    serial_number: str,
    product_model_id,
    location_id: int,
):
    repo = InventoryItemRepository(db_session)
    existing = await repo.find_by_serial_number(serial_number)
    if existing is not None:
        existing.status = InventoryStatus.AVAILABLE
        existing.product_model_id = product_model_id
        existing.current_location_id = location_id
        await db_session.flush()
        return existing
    return await repo.create(
        serial_number=serial_number,
        product_model_id=product_model_id,
        color="Black",
        current_location_id=location_id,
        status=InventoryStatus.AVAILABLE,
    )


MIXED_INVOICE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>mixed-invoice-guid-001</GUID>
  <MASTERID>20001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>501</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00501</REFERENCE>
  <DATE>20260705</DATE>
  <PARTYLEDGERNAME>Combo Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS Vivobook X1502ZA</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>125000.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>SN-MIX-LAPTOP-001</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS MD100 90NB0X02-M0A010</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>2500.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>SN-MIX-MOUSE-001</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


@pytest.mark.asyncio
async def test_expand_inventory_lines_splits_multiple_serials() -> None:
    vouchers = parse_vouchers_xml("""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
      <GUID>multi-serial-guid</GUID>
      <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
      <VOUCHERNUMBER>9</VOUCHERNUMBER>
      <DATE>20260705</DATE>
      <ALLINVENTORYENTRIES.LIST>
        <STOCKITEMNAME>ASUS MD100</STOCKITEMNAME>
        <ACTUALQTY>2 Nos</ACTUALQTY>
        <AMOUNT>5000.00</AMOUNT>
        <BATCHALLOCATIONS.LIST><SERIALNUMBER>ACC-001</SERIALNUMBER></BATCHALLOCATIONS.LIST>
        <BATCHALLOCATIONS.LIST><SERIALNUMBER>ACC-002</SERIALNUMBER></BATCHALLOCATIONS.LIST>
      </ALLINVENTORYENTRIES.LIST>
    </VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>""")
    expanded = expand_inventory_lines(vouchers[0].inventory_lines)
    assert len(expanded) == 2
    assert expanded[0].serial_number == "ACC-001"
    assert expanded[1].serial_number == "ACC-002"
    assert expanded[0].amount == "2500.00"
    assert expanded[1].amount == "2500.00"


@pytest.mark.asyncio
async def test_tally_sync_marks_laptop_and_accessory_sold_on_same_invoice(
    db_session: AsyncSession,
    initialized_system,
    brand,
    location,
    product_model,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    company_name = f"WEBSTUDIO-MIXED-{uuid.uuid4().hex[:8]}"
    await settings.set_value(
        "tally_company_name",
        company_name,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )

    accessory_model = await _ensure_accessory_model(db_session, brand)

    laptop_item = await _ensure_available_item(
        db_session,
        serial_number="SN-MIX-LAPTOP-001",
        product_model_id=product_model.id,
        location_id=location.id,
    )
    accessory_item = await _ensure_available_item(
        db_session,
        serial_number="SN-MIX-MOUSE-001",
        product_model_id=accessory_model.id,
        location_id=location.id,
    )
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        MIXED_INVOICE_XML,
        correlation_id="mixed-invoice-test",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 2

    await db_session.refresh(laptop_item)
    await db_session.refresh(accessory_item)
    assert laptop_item.status is InventoryStatus.SOLD
    assert accessory_item.status is InventoryStatus.SOLD

    sales_repo = SaleRepository(db_session)
    laptop_sale = await sales_repo.get_by_inventory_item_id(laptop_item.id)
    accessory_sale = await sales_repo.get_by_inventory_item_id(accessory_item.id)
    assert laptop_sale is not None
    assert accessory_sale is not None
    assert laptop_sale.printed_invoice_number == "WEB/25-26/00501"
    assert accessory_sale.printed_invoice_number == "WEB/25-26/00501"

    assert laptop_sale.sale_amount == 147500.0
    assert laptop_sale.sale_amount_excluding_gst == 125000.0
    assert accessory_sale.sale_amount == 2950.0
    assert accessory_sale.sale_amount_excluding_gst == 2500.0


@pytest.mark.asyncio
async def test_tally_sync_sells_by_serial_even_when_model_name_differs_and_serial_case_differs(
    db_session: AsyncSession,
    initialized_system,
    brand,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    ims_serial = f"SN-CASE-MOUSE-{suffix}"
    tally_serial = ims_serial.lower()
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>serial-case-mismatch-{suffix}</GUID>
  <MASTERID>20002</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>502</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00502</REFERENCE>
  <DATE>20260705</DATE>
  <PARTYLEDGERNAME>Case Test Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>Totally Different Product Name In Tally</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>2500.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>{tally_serial}</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""

    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    company_name = f"WEBSTUDIO-SERIAL-{uuid.uuid4().hex[:8]}"
    await settings.set_value(
        "tally_company_name",
        company_name,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )

    accessory_model = await _ensure_accessory_model(db_session, brand)

    item = await _ensure_available_item(
        db_session,
        serial_number=ims_serial,
        product_model_id=accessory_model.id,
        location_id=location.id,
    )
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        xml,
        correlation_id="serial-case-mismatch-test",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 1
    assert result.counters.model_mismatches == 1

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD

    sale = await SaleRepository(db_session).get_by_inventory_item_id(item.id)
    assert sale is not None
    assert sale.printed_invoice_number == "WEB/25-26/00502"
    assert sale.sale_amount == 2950.0
    assert sale.sale_amount_excluding_gst == 2500.0


@pytest.mark.asyncio
async def test_tally_sync_updates_last_successful_sync_at_when_one_sale_applied(
    db_session: AsyncSession,
    initialized_system,
    brand,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company_name = f"WEBSTUDIO-LAST-SYNC-{suffix}"
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

    accessory_model = await _ensure_accessory_model(db_session, brand)
    item = await _ensure_available_item(
        db_session,
        serial_number=f"SN-LAST-SYNC-{suffix}",
        product_model_id=accessory_model.id,
        location_id=location.id,
    )
    await db_session.commit()

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company_name)
    assert company_sync.last_successful_sync_at is None

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>last-sync-guid-{suffix}</GUID>
  <MASTERID>30001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>601</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00601</REFERENCE>
  <DATE>20260707</DATE>
  <PARTYLEDGERNAME>Last Sync Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS MD100 Silent Wireless Mouse</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>2500.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>SN-LAST-SYNC-{suffix}</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""

    result = await TallySyncService(db_session).process_voucher_xml(
        xml,
        correlation_id="last-successful-sync-test",
        company_name=company_name,
    )
    await db_session.commit()
    await db_session.refresh(company_sync)
    await db_session.refresh(item)

    assert result.counters.sales_created == 1
    assert company_sync.last_successful_sync_at is not None
    assert item.status is InventoryStatus.SOLD


@pytest.mark.asyncio
async def test_tally_sync_updates_last_successful_sync_at_on_partial_run(
    db_session: AsyncSession,
    initialized_system,
    brand,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company_name = f"WEBSTUDIO-PARTIAL-SYNC-{suffix}"
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

    accessory_model = await _ensure_accessory_model(db_session, brand)
    await _ensure_available_item(
        db_session,
        serial_number=f"SN-PARTIAL-OK-{suffix}",
        product_model_id=accessory_model.id,
        location_id=location.id,
    )
    await db_session.commit()

    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company_name)
    assert company_sync.last_successful_sync_at is None

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE>
<VOUCHER>
  <GUID>partial-good-{suffix}</GUID>
  <MASTERID>40001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>701</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00701</REFERENCE>
  <DATE>20260707</DATE>
  <PARTYLEDGERNAME>Partial Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS MD100 Silent Wireless Mouse</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>2500.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>SN-PARTIAL-OK-{suffix}</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER>
<VOUCHER>
  <GUID>partial-bad-{suffix}</GUID>
  <MASTERID>40002</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>702</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00702</REFERENCE>
  <DATE>20260707</DATE>
  <PARTYLEDGERNAME>Partial Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS MD100 Silent Wireless Mouse</STOCKITEMNAME>
    <ACTUALQTY>1 Nos</ACTUALQTY>
    <AMOUNT>2500.00</AMOUNT>
    <BATCHALLOCATIONS.LIST>
      <SERIALNUMBER>SN-DOES-NOT-EXIST-{suffix}</SERIALNUMBER>
    </BATCHALLOCATIONS.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER>
</TALLYMESSAGE></DATA></BODY></ENVELOPE>"""

    result = await TallySyncService(db_session).process_voucher_xml(
        xml,
        correlation_id="partial-last-successful-sync-test",
        company_name=company_name,
    )
    await db_session.commit()
    await db_session.refresh(company_sync)

    assert result.success is False
    assert result.counters.sales_created == 1
    assert result.counters.failures == 1
    assert company_sync.last_successful_sync_at is not None
