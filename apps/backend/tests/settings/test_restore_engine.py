"""Enterprise restore engine tests."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator
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
from webstudio_backend.services.backup_engine import BackupEngine
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.settings_service import SettingsService


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


@pytest_asyncio.fixture
async def backup_filename(
    api_client: AsyncClient,
    initialized_system,
) -> str:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    assert response.status_code == 200
    return response.json()["data"]["filename"]


@pytest.mark.asyncio
async def test_validate_backup_api(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups/validate",
        headers=headers,
        json={"filename": backup_filename, "source": "local"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["filename"] == backup_filename
    assert payload["integrity_valid"] is True
    assert payload["corruption_detected"] is False


@pytest.mark.asyncio
async def test_preview_restore_api(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups/preview",
        headers=headers,
        json={
            "filename": backup_filename,
            "restore_scope": "settings_only",
            "source": "local",
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["scope_implemented"] is True
    assert "affected_areas" in payload


@pytest.mark.asyncio
async def test_restore_settings_scope(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups/restore",
        headers=headers,
        json={
            "filename": backup_filename,
            "restore_scope": "settings_only",
            "source": "local",
            "create_emergency_backup": True,
            "confirmed": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["success"] is True
    assert payload["emergency_backup_filename"]
    assert payload["rollback_available"] is True


@pytest.mark.asyncio
async def test_restore_requires_confirmation(
    api_client: AsyncClient,
    initialized_system,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups/restore",
        headers=headers,
        json={
            "filename": backup_filename,
            "restore_scope": "entire_database",
            "confirmed": False,
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_restore_creates_audit_entry(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
    backup_filename: str,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    await api_client.post(
        "/api/v1/settings/backups/restore",
        headers=headers,
        json={
            "filename": backup_filename,
            "restore_scope": "settings_only",
            "confirmed": True,
        },
    )
    audits = await AuditLogRepository(db_session).search(
        AuditLogSearchFilters(entity_type="system"),
        PageParams(page=1, page_size=30),
    )
    descriptions = [entry.description or "" for entry in audits.items]
    assert any("Restore" in description for description in descriptions)


@pytest.mark.asyncio
async def test_import_backup_api(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
    test_settings: Settings,
    backup_filename: str,
) -> None:
    backup_dir = await SettingsService(db_session, test_settings).get_backup_folder_path()
    content = (backup_dir / backup_filename).read_bytes()
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.post(
        "/api/v1/settings/backups/import",
        headers=headers,
        files={"file": (backup_filename, content, "application/gzip")},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["filename"].startswith("webstudio-import-")
    assert payload["source"] == "imported"


@pytest.mark.asyncio
async def test_users_only_scope_not_implemented(
    db_session: AsyncSession,
    test_settings: Settings,
    tmp_path: Path,
) -> None:
    engine = BackupEngine(db_session, test_settings, backup_dir=tmp_path)
    created = await engine.create_backup(trigger_type="manual")
    restore = RestoreEngine(db_session, test_settings, backup_dir=tmp_path)
    preview = await restore.preview_restore(created.filename, restore_scope="users_only")
    assert preview.scope_implemented is False


@pytest.mark.asyncio
async def test_mark_completed_reinserts_when_restore_run_row_missing(
    db_session: AsyncSession,
) -> None:
    from sqlalchemy import delete

    from webstudio_backend.infrastructure.database.models.restore_run import RestoreRun
    from webstudio_backend.infrastructure.repositories.restore_run_repository import (
        RestoreRunRepository,
        RestoreRunSnapshot,
    )

    repo = RestoreRunRepository(db_session)
    run = await repo.create_run(
        filename="webstudio-backup-test.tar.gz",
        source="local",
        restore_scope="entire_database",
        actor_user_id=None,
        actor_display_name="System",
    )
    snapshot = RestoreRunSnapshot(
        id=run.id,
        filename=run.filename,
        source=run.source,
        restore_scope=run.restore_scope,
        actor_user_id=run.actor_user_id,
        actor_display_name=run.actor_display_name,
    )
    await db_session.execute(delete(RestoreRun).where(RestoreRun.id == run.id))
    await db_session.flush()

    completed = await repo.mark_completed(
        snapshot,
        emergency_backup_filename=None,
        duration_ms=42,
        verification_status="success",
        warnings=[],
        errors=[],
    )
    assert completed.status == "completed"
    assert completed.verification_status == "success"
    assert completed.duration_ms == 42
    assert completed.id != snapshot.id
