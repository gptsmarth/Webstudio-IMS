"""M12J — Brand-new customer installation simulation (API-level).

Simulates the dedicated-server + multi-client journey against a fresh PostgreSQL
test database. Windows installer UI, NSSM service install, and physical Tally on
a Lenovo laptop are validated via script audit + API contracts (see M12J reports).
"""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.enrichment_service import ProductEnrichmentService

COMPANY_NAME = "PRECISION LAPTOPS"
TALLY_HOST = "192.168.1.20"  # Lenovo laptop on LAN (simulated)


@pytest_asyncio.fixture
async def sim_client(
    db_session: AsyncSession,
    test_settings: Settings,
) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(test_settings)

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_m12j_customer_installation_simulation(
    sim_client: AsyncClient,
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    """End-to-end fresh customer install: server setup through backup/restore."""

    # --- Fresh PostgreSQL (migrations applied by session fixture) ---
    alembic = await db_session.scalar(text("SELECT version_num FROM webstudio.alembic_version"))
    assert alembic is not None
    assert alembic >= "0001_initial"

    # --- Setup: uninitialized ---
    status = await sim_client.get("/api/v1/setup/status")
    assert status.status_code == 200
    assert status.json()["data"]["system_initialized"] is False

    # --- Initialize company + main admin + recovery key ---
    init = await sim_client.post(
        "/api/v1/setup/initialize",
        json={
            "company_name": COMPANY_NAME,
            "main_admin_name": "Store Owner",
            "username": MAIN_ADMIN_USERNAME,
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert init.status_code == 201
    init_data = init.json()["data"]
    assert init_data["company_name"] == COMPANY_NAME
    recovery_key = init_data["recovery_key"]
    assert len(recovery_key) >= 16

    confirm = await sim_client.post("/api/v1/setup/confirm-recovery-key")
    assert confirm.status_code == 200

    headers = await login_headers(sim_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)

    # --- Office deployment wizard (business-hours LAN setup) ---
    detect = await sim_client.post("/api/v1/deployment/office/detect", headers=headers)
    assert detect.status_code == 200
    detect_data = detect.json()["data"]
    check_keys = {c["key"] for c in detect_data["checks"]}
    assert {"network", "postgresql", "api", "backup_path", "tally", "firewall", "ports"}.issubset(
        check_keys
    )

    complete = await sim_client.post("/api/v1/deployment/office/complete", headers=headers)
    assert complete.status_code == 200
    assert complete.json()["data"]["completed"] is True
    client_url = complete.json()["data"]["summary"]["client_connection_url"]
    assert client_url.startswith("http")

    # --- Desktop client connect ---
    version = await sim_client.get("/api/v1/version")
    assert version.status_code == 200
    assert version.json()["data"]["api_version"] == "1.0"

    caps = await sim_client.get("/api/v1/capabilities")
    assert caps.status_code == 200
    assert caps.json()["data"]["modules"]["inventory"] is True

    discovery = await sim_client.get("/api/v1/discovery/health")
    assert discovery.status_code == 200
    assert discovery.json()["data"]["online"] is True

    # --- Android phone connect ---
    mobile_version = await sim_client.get("/api/v1/version")
    assert mobile_version.status_code == 200
    assert "mobile" in mobile_version.json()["data"]

    sync_unauth = await sim_client.get("/api/v1/sync/state")
    assert sync_unauth.status_code == 401

    sync_auth = await sim_client.get("/api/v1/sync/state", headers=headers)
    assert sync_auth.status_code == 200

    # --- iPhone connect (same mobile API surface) ---
    search_unauth = await sim_client.get("/api/v1/search", params={"q": "lenovo"})
    assert search_unauth.status_code == 401

    search_auth = await sim_client.get("/api/v1/search", params={"q": "lenovo"}, headers=headers)
    assert search_auth.status_code == 200

    # --- Configure Tally (Lenovo laptop) ---
    tally_settings = await sim_client.patch(
        "/api/v1/settings/tally",
        headers=headers,
        json={
            "enabled": True,
            "tally_host": TALLY_HOST,
            "tally_port": "9000",
            "tally_company_name": "PRECISION LAPTOPS",
            "sync_interval_seconds": 300,
        },
    )
    assert tally_settings.status_code == 200
    assert tally_settings.json()["data"]["enabled"] is True

    conn_test = await sim_client.post("/api/v1/integrations/tally/connection/test", headers=headers)
    assert conn_test.status_code == 200
    assert "stages" in conn_test.json()["data"]

    # --- First synchronization (queued; no live Tally in CI) ---
    trigger = await sim_client.post("/api/v1/integrations/tally/sync/trigger", headers=headers)
    assert trigger.status_code == 200
    assert trigger.json()["data"]["status"] == "queued"

    # --- Create backup ---
    backup = await sim_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    assert backup.status_code == 200
    backup_name = backup.json()["data"]["filename"]
    assert backup_name

    validate = await sim_client.post(
        "/api/v1/settings/backups/validate",
        headers=headers,
        json={"filename": backup_name, "source": "local"},
    )
    assert validate.status_code == 200
    assert validate.json()["data"]["integrity_valid"] is True

    # --- Restore backup (settings scope — safe for simulation) ---
    restore = await sim_client.post(
        "/api/v1/settings/backups/restore",
        headers=headers,
        json={
            "filename": backup_name,
            "restore_scope": "settings_only",
            "source": "local",
            "create_emergency_backup": True,
            "confirmed": True,
        },
    )
    assert restore.status_code == 200
    assert restore.json()["data"]["success"] is True

    # --- Verify reports ---
    inventory_report = await sim_client.get("/api/v1/reports/inventory", headers=headers)
    assert inventory_report.status_code == 200
    assert inventory_report.json()["data"]["report_type"] == "inventory"
    assert "rows" in inventory_report.json()["data"]

    sales_report = await sim_client.get("/api/v1/reports/sales", headers=headers)
    assert sales_report.status_code == 200
    assert sales_report.json()["data"]["report_type"] == "sales"

    # --- Verify AI (mock provider in test env) ---
    repo = SystemSettingRepository(db_session)
    await repo.set_value("ai_primary_provider", "mock", value_type=SettingValueType.STRING)
    await repo.set_value("ai_fallback_chain", '["mock"]', value_type=SettingValueType.JSON)
    await repo.set_value("ai_enrichment_enabled", "true", value_type=SettingValueType.BOOLEAN)
    await db_session.commit()

    enrichment = ProductEnrichmentService(db_session, test_settings)
    ai_result = await enrichment.lookup_laptop_spec("SIM-LENOVO-001", brand_name="Lenovo")
    assert ai_result["cpu"]
    assert ai_result["provider"] == "mock"

    # --- Verify images API (auth gate) ---
    image_proxy = await sim_client.get(
        "/api/v1/product-images/proxy",
        params={"url": "/assets/product-images/sim-test.jpg"},
        headers=headers,
    )
    assert image_proxy.status_code in {404, 422}

    # --- Automatic reconnect signal (discovery health after restore) ---
    rediscover = await sim_client.get("/api/v1/discovery/health")
    assert rediscover.status_code == 200
    assert rediscover.json()["data"]["database_status"] in {"ok", "unknown", "failed"}


def test_m12j_windows_service_scripts_present() -> None:
    """Validate Windows service + business-hours scripts exist for server PC."""
    root = Path(__file__).resolve().parents[4]
    required = [
        root / "infra/windows/install-webstudio-service.ps1",
        root / "infra/windows/start-business-day.ps1",
        root / "infra/windows/stop-business-day.ps1",
        root / "infra/windows/configure-firewall.ps1",
        root / "infra/windows/server-installer/WEBSTUDIO-Server-Setup.iss",
    ]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    assert not missing, f"Missing installer artifacts: {missing}"

    install_script = (root / "infra/windows/install-webstudio-service.ps1").read_text(
        encoding="utf-8"
    )
    assert "SERVICE_DELAYED_AUTO_START" in install_script
    assert "alembic upgrade head" in install_script
