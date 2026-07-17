"""Tests for EAN-as-serial (per-brand allow_duplicate_serials) mode.

Covers:
  * A duplicate-serial brand lets many units share one serial (the EAN),
    each flagged serial_is_shared, while normal brands still reject duplicates.
  * Tally sales sync deducts a billed quantity from the shared EAN pool (FIFO).
  * Oversell (billed > available) sells what exists and flags review.
  * An exhausted pool (nothing available) blocks the sale and flags review.

Each test uses a unique brand / model / EAN suffix because the Tally sync path
commits to the shared test database — this keeps the tests isolated.
"""

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
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateSerialNumberError
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.tally_sync_service import TallySyncService


def _suffix() -> str:
    return uuid.uuid4().hex[:8].upper()


async def _ean_brand(db_session: AsyncSession, *, name: str) -> Brand:
    return await BrandRepository(db_session).create(name, allow_duplicate_serials=True)


async def _controller_model(
    db_session: AsyncSession, brand: Brand, *, model_number: str
) -> ProductModel:
    return await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.OTHER,
        model_number=model_number,
        model_name=f"{model_number} Gaming Controller",
        actor=AuditActor.system(),
    )


async def _add_shared_units(
    db_session: AsyncSession,
    *,
    product_model_id,
    location_id: int,
    count: int,
    serial: str,
) -> list:
    repo = InventoryItemRepository(db_session)
    created = []
    for _ in range(count):
        created.append(
            await repo.create(
                serial_number=serial,
                product_model_id=product_model_id,
                color="Black",
                current_location_id=location_id,
                status=InventoryStatus.AVAILABLE,
            )
        )
    return created


async def _enable_tally(db_session: AsyncSession, suffix: str) -> str:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    company_name = f"WEBSTUDIO-EAN-{suffix}"
    await settings.set_value(
        "tally_company_name",
        company_name,
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )
    return company_name


def _ean_sale_xml(*, guid: str, qty: int, serial: str, model_number: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>90001</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>901</VOUCHERNUMBER>
  <REFERENCE>WEB/25-26/00901</REFERENCE>
  <DATE>20260710</DATE>
  <PARTYLEDGERNAME>EAN Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>{model_number} Gaming Controller</STOCKITEMNAME>
    <ACTUALQTY>{qty} Nos</ACTUALQTY>
    <AMOUNT>{qty * 1500}.00</AMOUNT>
    <BASICUSERDESCRIPTION.LIST>
      <BASICUSERDESCRIPTION>{serial}</BASICUSERDESCRIPTION>
    </BASICUSERDESCRIPTION.LIST>
  </ALLINVENTORYENTRIES.LIST>
</VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""


@pytest.mark.asyncio
async def test_ean_brand_allows_duplicate_serials_and_flags_shared(
    db_session: AsyncSession,
    initialized_system,
    location,
) -> None:
    suffix = _suffix()
    brand = await _ean_brand(db_session, name=f"GamePro-{suffix}")
    model = await _controller_model(db_session, brand, model_number=f"GP{suffix}")
    ean = f"EAN{suffix}"

    units = await _add_shared_units(
        db_session, product_model_id=model.id, location_id=location.id, count=3, serial=ean
    )

    assert len(units) == 3
    assert all(unit.serial_number == ean for unit in units)
    assert all(unit.serial_is_shared is True for unit in units)


@pytest.mark.asyncio
async def test_normal_brand_still_rejects_duplicate_serial(
    db_session: AsyncSession,
    initialized_system,
    location,
) -> None:
    suffix = _suffix()
    normal = await BrandRepository(db_session).create(f"Normal-{suffix}")
    assert normal.allow_duplicate_serials is False

    model = await ProductModelRepository(db_session).create(
        brand_id=normal.id,
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.OTHER,
        model_number=f"ACC{suffix}",
        model_name="Unique Accessory",
        actor=AuditActor.system(),
    )
    inv = InventoryItemRepository(db_session)
    serial = f"UNIQUE-SN-{suffix}"
    await inv.create(
        serial_number=serial,
        product_model_id=model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    with pytest.raises(DuplicateSerialNumberError):
        await inv.create(
            serial_number=serial,
            product_model_id=model.id,
            color="Black",
            current_location_id=location.id,
            status=InventoryStatus.AVAILABLE,
        )


@pytest.mark.asyncio
async def test_tally_sells_quantity_from_ean_pool_fifo(
    db_session: AsyncSession,
    initialized_system,
    location,
) -> None:
    suffix = _suffix()
    company_name = await _enable_tally(db_session, suffix)
    brand = await _ean_brand(db_session, name=f"GamePro-{suffix}")
    model_number = f"GP{suffix}"
    model = await _controller_model(db_session, brand, model_number=model_number)
    ean = f"EAN{suffix}"
    await _add_shared_units(
        db_session, product_model_id=model.id, location_id=location.id, count=5, serial=ean
    )
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        _ean_sale_xml(guid=f"ean-qty-{suffix}", qty=2, serial=ean, model_number=model_number),
        correlation_id="ean-qty-test",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 2

    inv = InventoryItemRepository(db_session)
    remaining = await inv.find_available_shared_units_fifo(serial_number=ean, limit=100)
    assert len(remaining) == 3


@pytest.mark.asyncio
async def test_tally_ean_oversell_sells_available_and_flags_review(
    db_session: AsyncSession,
    initialized_system,
    location,
) -> None:
    suffix = _suffix()
    company_name = await _enable_tally(db_session, suffix)
    brand = await _ean_brand(db_session, name=f"GamePro-{suffix}")
    model_number = f"GP{suffix}"
    model = await _controller_model(db_session, brand, model_number=model_number)
    ean = f"EAN{suffix}"
    await _add_shared_units(
        db_session, product_model_id=model.id, location_id=location.id, count=2, serial=ean
    )
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        _ean_sale_xml(guid=f"ean-oversell-{suffix}", qty=5, serial=ean, model_number=model_number),
        correlation_id="ean-oversell-test",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    # Only the 2 available units are sold; the 3-unit shortfall is flagged.
    assert result.counters.sales_created == 2

    inv = InventoryItemRepository(db_session)
    remaining = await inv.find_available_shared_units_fifo(serial_number=ean, limit=100)
    assert len(remaining) == 0


@pytest.mark.asyncio
async def test_tally_ean_exhausted_pool_blocks_sale(
    db_session: AsyncSession,
    initialized_system,
    location,
) -> None:
    suffix = _suffix()
    company_name = await _enable_tally(db_session, suffix)
    brand = await _ean_brand(db_session, name=f"GamePro-{suffix}")
    model_number = f"GP{suffix}"
    model = await _controller_model(db_session, brand, model_number=model_number)
    ean = f"EAN{suffix}"
    units = await _add_shared_units(
        db_session, product_model_id=model.id, location_id=location.id, count=1, serial=ean
    )
    # Pre-sell the only unit so the pool is exhausted.
    units[0].status = InventoryStatus.SOLD
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        _ean_sale_xml(guid=f"ean-exhausted-{suffix}", qty=1, serial=ean, model_number=model_number),
        correlation_id="ean-exhausted-test",
        company_name=company_name,
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created == 0
