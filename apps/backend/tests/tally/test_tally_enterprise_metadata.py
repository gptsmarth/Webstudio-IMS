"""M12E — ensure Tally internal metadata never leaks to client APIs."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import SaleSource
from webstudio_backend.infrastructure.database.models.sale import Sale

FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "guid",
        "master_id",
        "alter_id",
        "tally_voucher_guid",
        "tally_master_id",
        "last_processed_guid",
        "last_processed_master_id",
        "sync_run_id",
    }
)


def _assert_no_forbidden_keys(payload: object, *, path: str = "root") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            normalized = key.lower()
            assert normalized not in FORBIDDEN_PUBLIC_KEYS, f"Forbidden key {key!r} at {path}"
            _assert_no_forbidden_keys(value, path=f"{path}.{key}")
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            _assert_no_forbidden_keys(item, path=f"{path}[{index}]")


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
async def test_tally_dashboard_operational_fields_without_internal_metadata(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/integrations/tally/dashboard", headers=headers)
    assert response.status_code == 200
    payload = response.json()["data"]
    _assert_no_forbidden_keys(payload)

    operational = payload["operational"]
    for field in (
        "last_successful_sync_at",
        "last_invoice_imported",
        "last_invoice_date",
        "next_scheduled_sync_at",
        "imported_today",
        "imported_this_week",
        "imported_this_month",
        "sync_health",
    ):
        assert field in operational, f"Missing operational field: {field}"


@pytest.mark.asyncio
async def test_tally_sync_history_without_internal_metadata(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/integrations/tally/sync/history", headers=headers)
    assert response.status_code == 200
    _assert_no_forbidden_keys(response.json()["data"])


@pytest.mark.asyncio
async def test_sale_detail_omits_tally_internal_identifiers(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    sale = Sale(
        inventory_item_id=None,
        sale_source=SaleSource.TALLY,
        sold_at=datetime.now(UTC),
        invoice_number="TALLY-INV-001",
        snapshot_serial_number="SN-HIDDEN-001",
        snapshot_brand_name="HP",
        snapshot_model_number="840",
        snapshot_model_name="EliteBook",
        snapshot_location_name="Store",
        tally_voucher_guid="secret-guid-must-not-leak",
        tally_master_id="99999",
        printed_invoice_number="WEB/25-26/00001",
        tally_voucher_number="101",
    )
    db_session.add(sale)
    await db_session.commit()
    await db_session.refresh(sale)

    response = await api_client.get(f"/api/v1/sales/{sale.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    _assert_no_forbidden_keys(data)
    assert "tally_voucher_guid" not in data
    assert "tally_master_id" not in data
    assert data["printed_invoice_number"] == "WEB/25-26/00001"
