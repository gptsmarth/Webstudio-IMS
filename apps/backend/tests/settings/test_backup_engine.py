"""Enterprise backup engine tests."""

from __future__ import annotations

import subprocess

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.audit_log_repository import AuditLogRepository
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.services.backup_schedule import (
    backup_health_status,
    compute_next_scheduled_backup,
)


@pytest_asyncio.fixture
async def api_client(
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
async def test_create_enterprise_backup(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["filename"].endswith(".tar.gz")
    assert payload["verification_status"] in {"success", "warning"}
    assert payload["checksum_sha256"]
    assert payload["size_bytes"] > 0

    runs = await BackupRunRepository(db_session).list_recent(limit=5)
    assert len(runs) >= 1
    assert runs[0].filename == payload["filename"]

    details = await api_client.get(
        f"/api/v1/settings/backups/{payload['filename']}/details",
        headers=headers,
    )
    manifest = details.json()["data"]["manifest"]
    assert manifest["backup_version"] == "2.1"
    assert manifest["company_name"] is not None
    assert manifest["inventory_count"] is not None
    assert manifest["checksum"]


@pytest.mark.asyncio
async def test_backup_preview_and_validate_enterprise_fields(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    create = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    filename = create.json()["data"]["filename"]
    validate = await api_client.post(
        "/api/v1/settings/backups/validate",
        headers=headers,
        json={"filename": filename, "source": "local"},
    )
    assert validate.status_code == 200
    body = validate.json()["data"]
    assert "compatibility_report" in body
    assert body["restore_allowed"] is True

    preview = await api_client.post(
        "/api/v1/settings/backups/preview",
        headers=headers,
        json={"filename": filename, "restore_scope": "entire_database", "source": "local"},
    )
    assert preview.status_code == 200
    preview_body = preview.json()["data"]
    assert preview_body["compressed_size_bytes"] > 0
    assert "company_name" in preview_body


@pytest.mark.asyncio
async def test_backup_workspace_dashboard_fields(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    backup = response.json()["data"]["backup"]
    assert "health_status" in backup
    assert "schedule" in backup
    assert "retention_count" in backup
    assert "next_scheduled_backup_at" in backup
    assert "storage_backend" in backup


@pytest.mark.asyncio
async def test_backup_policy_patch(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    body = {
        "backup_folder": "backups",
        "storage_backend": "local",
        "schedule": "daily",
        "retention_count": 14,
    }
    response = await api_client.patch("/api/v1/settings/backup", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()["data"]
    assert updated["schedule"] == "daily"
    assert updated["retention_count"] == 14


@pytest.mark.asyncio
async def test_backup_creates_audit_entry(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    await api_client.post("/api/v1/settings/backups", headers=headers, json={})
    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(entity_type="system"),
        PageParams(page=1, page_size=20),
    )
    descriptions = [entry.description or "" for entry in audits.items]
    assert any("Backup" in description for description in descriptions)


def test_compute_next_scheduled_backup_daily() -> None:
    last = datetime(2026, 1, 1, tzinfo=UTC)
    next_at = compute_next_scheduled_backup("daily", last_backup_at=last)
    assert next_at is not None
    assert next_at > last


def test_backup_health_status_degraded_when_database_unhealthy() -> None:
    assert (
        backup_health_status(
            database_health="failed",
            last_verification_status="success",
            storage_free_bytes=10_000_000_000,
        )
        == "degraded"
    )


def test_postgres_connection_uses_database_url_and_tcp_host() -> None:
    from webstudio_backend.core.config import Settings
    from webstudio_backend.services.backup_engine import BackupEngine

    engine = BackupEngine(
        session=object(),  # type: ignore[arg-type]
        app_settings=Settings(
            database_url="postgresql+asyncpg://webstudio_app:secret@localhost:5432/webstudio_dev",
        ),
    )
    user, password, host, port, db_name = engine._postgres_connection()
    assert user == "webstudio_app"
    assert password == "secret"
    assert host == "127.0.0.1"
    assert port == "5432"
    assert db_name == "webstudio_dev"


def test_psql_restore_falls_back_when_docker_compose_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from webstudio_backend.core.config import Settings
    from webstudio_backend.services.backup_engine import BackupEngine

    sql_path = tmp_path / "database.sql"
    sql_path.write_text("SELECT 1;\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        if cmd[0] == "docker":
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    engine = BackupEngine(
        session=object(),  # type: ignore[arg-type]
        app_settings=Settings(
            database_url="postgresql+asyncpg://webstudio_app:secret@localhost:5432/webstudio_test",
            app_env="test",
        ),
    )
    engine._psql_restore_from_file(sql_path, on_error_stop=True)

    assert calls[0][0] == "docker"
    assert calls[1][0] == "psql"
    assert "127.0.0.1" in calls[1]
    assert "webstudio_test" in calls[1]
