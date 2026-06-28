"""Tally integration API tests."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from .fixtures.sample_vouchers import SAMPLE_VOUCHER_XML
from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import InventoryStatus, SettingValueType
from webstudio_backend.infrastructure.repositories.inventory_item_repository import InventoryItemRepository
from webstudio_backend.infrastructure.repositories.system_setting_repository import SystemSettingRepository
from webstudio_backend.integrations.tally.xml_parser import parse_vouchers_xml
from webstudio_backend.services.tally_sync_service import TallySyncService


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
async def test_tally_dashboard_requires_auth(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/integrations/tally/dashboard")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_parse_sample_voucher_xml() -> None:
    vouchers = parse_vouchers_xml(SAMPLE_VOUCHER_XML)
    assert len(vouchers) == 2
    sales_voucher = vouchers[0]
    assert sales_voucher.voucher_type == "Sales"
    assert sales_voucher.printed_invoice_number == "WEB/24-25/00042"
    assert sales_voucher.voucher_number == "42"
    assert sales_voucher.inventory_lines[0].serial_number == "SN-TALLY-001"


@pytest.mark.asyncio
async def test_parse_production_style_basicuserdescription_serial() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><BODY><DATA><TALLYMESSAGE><VOUCHER>
      <GUID>prod-guid-001</GUID>
      <MASTERID>68580</MASTERID>
      <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
      <VOUCHERNUMBER>325</VOUCHERNUMBER>
      <DATE>20260627</DATE>
      <ALLINVENTORYENTRIES.LIST>
        <STOCKITEMNAME>ACER ASPIRE A325-45-V2 UN.36FSI.00B</STOCKITEMNAME>
        <ACTUALQTY>1 NOS.</ACTUALQTY>
        <BASICUSERDESCRIPTION.LIST>
          <BASICUSERDESCRIPTION>UN36FSI00B613004C20700</BASICUSERDESCRIPTION>
        </BASICUSERDESCRIPTION.LIST>
      </ALLINVENTORYENTRIES.LIST>
    </VOUCHER></TALLYMESSAGE></DATA></BODY></ENVELOPE>"""
    vouchers = parse_vouchers_xml(xml)
    assert len(vouchers) == 1
    assert vouchers[0].inventory_lines[0].serial_number == "UN36FSI00B613004C20700"


@pytest.mark.asyncio
async def test_tally_xml_processing_creates_sale(
    db_session: AsyncSession,
    initialized_system,
    product_model,
    location,
) -> None:
    settings = SystemSettingRepository(db_session)
    await settings.set_value("tally_enabled", "true", value_type=SettingValueType.BOOLEAN, updated_by_user_id=1)
    await settings.set_value(
        "tally_company_name",
        "WEBSTUDIO",
        value_type=SettingValueType.STRING,
        updated_by_user_id=1,
    )

    inventory_repo = InventoryItemRepository(db_session)
    await inventory_repo.create(
        serial_number="SN-TALLY-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    result = await TallySyncService(db_session).process_voucher_xml(
        SAMPLE_VOUCHER_XML,
        correlation_id="test-correlation",
        company_name="WEBSTUDIO",
    )
    await db_session.commit()

    assert result.success is True
    assert result.counters.sales_created >= 1

    item = await inventory_repo.find_by_serial_number("SN-TALLY-001")
    assert item is not None
    assert item.status is InventoryStatus.SOLD


@pytest.mark.asyncio
async def test_tally_dashboard_for_admin(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/integrations/tally/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    assert "connection_status" in payload
    assert "voucher_types" in payload
    assert "Sales" in payload["voucher_types"]
    assert "NEW SALE" in payload["voucher_types"]
