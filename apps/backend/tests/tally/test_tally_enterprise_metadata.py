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
        "sync_run_id",
    }
)

# Main Admin diagnostics under operational.sync_checkpoint (GUID watermark audit).
CHECKPOINT_DIAGNOSTIC_KEYS = frozenset(
    {
        "last_processed_guid",
        "last_processed_master_id",
        "last_processed_voucher_type",
        "last_processed_invoice_number",
        "last_imported_voucher_date",
        "last_successful_sync_at",
        "scheduler_status",
        "scheduler_status_label",
    }
)


def _assert_no_forbidden_keys(payload: object, *, path: str = "root") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}"
            normalized = key.lower()
            if path.endswith(".sync_checkpoint") or key == "sync_checkpoint":
                _assert_no_forbidden_keys(value, path=child_path)
                continue
            assert normalized not in FORBIDDEN_PUBLIC_KEYS, f"Forbidden key {key!r} at {path}"
            assert normalized not in {
                "last_processed_guid",
                "last_processed_master_id",
            }, f"Checkpoint key {key!r} must live under operational.sync_checkpoint (at {path})"
            _assert_no_forbidden_keys(value, path=child_path)
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
        "sync_checkpoint",
    ):
        assert field in operational, f"Missing operational field: {field}"

    checkpoint = operational["sync_checkpoint"]
    for field in CHECKPOINT_DIAGNOSTIC_KEYS:
        assert field in checkpoint, f"Missing sync_checkpoint field: {field}"


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
async def test_sale_detail_exposes_tally_identifiers_and_review_fields(
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
        snapshot_serial_number="SN-VISIBLE-001",
        snapshot_brand_name="HP",
        snapshot_model_number="840",
        snapshot_model_name="EliteBook",
        snapshot_location_name="Store",
        tally_voucher_guid="guid-for-sale-detail",
        tally_master_id="99999",
        printed_invoice_number="WEB/25-26/00001",
        tally_voucher_number="101",
        review_required=True,
        review_reason="Model description differs after serial match.",
        invoice_model_name="Invoice Model",
        ims_model_name="IMS Model",
    )
    db_session.add(sale)
    await db_session.commit()
    await db_session.refresh(sale)

    response = await api_client.get(f"/api/v1/sales/{sale.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["tally_voucher_guid"] == "guid-for-sale-detail"
    assert data["tally_master_id"] == "99999"
    assert data["printed_invoice_number"] == "WEB/25-26/00001"
    assert data["review_required"] is True
    assert data["review_reason"] == "Model description differs after serial match."
    assert data["invoice_model_name"] == "Invoice Model"
    assert data["ims_model_name"] == "IMS Model"
    assert data["original_xml_available"] is False
    assert data["additional_products"] == []
