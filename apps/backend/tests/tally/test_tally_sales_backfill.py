"""Historical sales backfill (additive feature).

Proves that ``backfill_sales``:
  * processes past invoices that the incremental watermark would skip,
  * marks matching serials sold exactly once (idempotent re-runs),
  * never advances the incremental GUID watermark,
  * returns an accurate summary.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytest_plugins = ["auth.conftest"]

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
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
from webstudio_backend.services.tally_connectivity_service import TallyConnectivityService
from webstudio_backend.services.tally_sync_service import TallySyncService


def _envelope(vouchers_xml: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f"<ENVELOPE><BODY><DATA><TALLYMESSAGE>{vouchers_xml}"
        "</TALLYMESSAGE></DATA></BODY></ENVELOPE>"
    )


def _sale_voucher_xml(
    *,
    guid: str,
    serial: str,
    invoice: str,
    master_id: str = "91001",
    voucher_date: str = "20260601",
) -> str:
    return f"""<VOUCHER>
  <GUID>{guid}</GUID>
  <MASTERID>{master_id}</MASTERID>
  <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
  <VOUCHERNUMBER>{invoice}</VOUCHERNUMBER>
  <REFERENCE>{invoice}</REFERENCE>
  <DATE>{voucher_date}</DATE>
  <PARTYLEDGERNAME>Backfill Buyer</PARTYLEDGERNAME>
  <ALLINVENTORYENTRIES.LIST>
    <STOCKITEMNAME>ASUS X1502ZA-EJ541WS</STOCKITEMNAME>
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


def _patched_connectivity(day_book_xml: str):
    """Patch connectivity so no real Tally is contacted (read-only fake export)."""
    diagnostics = SimpleNamespace(reachable=True, user_message="")
    fake_client = SimpleNamespace(
        export_monitored_voucher_types=AsyncMock(return_value={"day_book": day_book_xml}),
    )
    reachable = patch.object(
        TallyConnectivityService,
        "ensure_workstation_reachable",
        new=AsyncMock(return_value=diagnostics),
    )
    build = patch.object(
        TallyConnectivityService,
        "build_client_for_sync",
        new=AsyncMock(return_value=fake_client),
    )
    return reachable, build, fake_client


@pytest.mark.asyncio
async def test_backfill_sales_marks_historical_invoice_sold(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"BF-SALES-{suffix}"
    serial = f"BF-SN-{suffix}"
    guid = f"bf-guid-{suffix}"
    await _enable(db_session, company)

    inventory = InventoryItemRepository(db_session)
    item = await inventory.create(
        serial_number=serial,
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )

    # Simulate an ALREADY-ADVANCED watermark (regular sync would skip this GUID).
    company_sync = await TallyCompanySyncRepository(db_session).get_or_create(company)
    company_sync.last_processed_guid = f"zz-newer-{suffix}"
    company_sync.last_imported_voucher_date = date(2026, 7, 15)
    await db_session.commit()

    xml = _envelope(_sale_voucher_xml(guid=guid, serial=serial, invoice=f"BF/{suffix}"))
    service = TallySyncService(db_session)
    reachable, build, fake_client = _patched_connectivity(xml)
    with reachable, build:
        summary = await service.backfill_sales(
            from_date=date(2026, 6, 1),
            to_date=date(2026, 6, 30),
            correlation_id="bf-test-1",
        )
    await db_session.commit()

    assert summary["fetched"] == 1
    assert summary["checked"] == 1
    assert summary["imported"] == 1
    assert summary["sales_created"] == 1
    assert summary["failures"] == 0

    # Client was asked for the requested window.
    call_kwargs = fake_client.export_monitored_voucher_types.await_args.kwargs
    assert call_kwargs["from_date"] == date(2026, 6, 1)
    assert call_kwargs["to_date"] == date(2026, 6, 30)

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD
    sale = await SaleRepository(db_session).get_by_inventory_item_id(item.id)
    assert sale is not None
    assert sale.tally_voucher_guid == guid

    # Incremental watermark untouched — regular sync resumes where it was.
    await db_session.refresh(company_sync)
    assert company_sync.last_processed_guid == f"zz-newer-{suffix}"
    assert company_sync.last_imported_voucher_date == date(2026, 7, 15)


@pytest.mark.asyncio
async def test_backfill_sales_is_idempotent(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    company = f"BF-IDEM-{suffix}"
    serial = f"BF-IDEM-SN-{suffix}"
    guid = f"bf-idem-guid-{suffix}"
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

    xml = _envelope(_sale_voucher_xml(guid=guid, serial=serial, invoice=f"BFI/{suffix}"))
    service = TallySyncService(db_session)

    reachable, build, _ = _patched_connectivity(xml)
    with reachable, build:
        first = await service.backfill_sales(
            from_date=date(2026, 6, 1),
            correlation_id="bf-idem-1",
        )
    await db_session.commit()
    assert first["sales_created"] == 1

    reachable, build, _ = _patched_connectivity(xml)
    with reachable, build:
        second = await service.backfill_sales(
            from_date=date(2026, 6, 1),
            correlation_id="bf-idem-2",
        )
    await db_session.commit()

    assert second["sales_created"] == 0
    assert second["skipped"] == 1
    assert second["imported"] == 0

    await db_session.refresh(item)
    assert item.status is InventoryStatus.SOLD
    sale = await SaleRepository(db_session).get_by_inventory_item_id(item.id)
    assert sale is not None


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(get_settings())

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_sales_backfill_endpoint_requires_tally_enabled(
    api_client: AsyncClient,
    db_session: AsyncSession,
    initialized_system,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value(
        "tally_enabled", "false", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1
    )
    await db_session.commit()
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/integrations/tally/sales/backfill",
        headers=headers,
        json={"from_date": "2026-06-01"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_sales_backfill_endpoint_rejects_inverted_range(
    api_client: AsyncClient,
    db_session: AsyncSession,
    initialized_system,
) -> None:
    suffix = uuid.uuid4().hex[:8].upper()
    await _enable(db_session, f"BF-RANGE-{suffix}")
    await db_session.commit()
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/integrations/tally/sales/backfill",
        headers=headers,
        json={"from_date": "2026-06-30", "to_date": "2026-06-01"},
    )
    assert response.status_code == 422
