"""Google Drive cloud backup sync tests — the real Drive API is never called."""

from __future__ import annotations

pytest_plugins = ["auth.conftest"]

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from auth.conftest import MAIN_ADMIN_USERNAME, TEST_PASSWORD, login_headers
from webstudio_backend.app import create_app
from webstudio_backend.core.config import Settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.repositories.backup_run_repository import BackupRunRepository
from webstudio_backend.infrastructure.repositories.cloud_backup_connection_repository import (
    GOOGLE_DRIVE_PROVIDER,
    CloudBackupConnectionRepository,
)
from webstudio_backend.infrastructure.security.secret_encryption import encrypt_secret
from webstudio_backend.services import cloud_backup_sync_scheduler as scheduler_module
from webstudio_backend.services import google_drive_client as drive_client_module
from webstudio_backend.services.cloud_backup_sync_scheduler import run_cloud_backup_sync
from webstudio_backend.services.google_drive_client import GoogleDriveClient, GoogleDriveError


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


def _stub_ensure_backup_folder(
    monkeypatch: pytest.MonkeyPatch, folder_id: str = "folder-1"
) -> None:
    monkeypatch.setattr(GoogleDriveClient, "ensure_backup_folder", lambda self: folder_id)


@pytest.mark.asyncio
async def test_connect_google_drive(
    api_client: AsyncClient,
    initialized_system,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_ensure_backup_folder(monkeypatch)
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)

    response = await api_client.post(
        "/api/v1/settings/backups/cloud/google-drive/connect",
        headers=headers,
        json={"refresh_token": "fake-refresh-token", "account_email": "shop@example.com"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["connected"] is True
    assert payload["account_email"] == "shop@example.com"
    assert payload["status"] == "connected"

    status_response = await api_client.get(
        "/api/v1/settings/backups/cloud/status",
        headers=headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["data"]["connected"] is True


@pytest.mark.asyncio
async def test_disconnect_clears_credentials_not_history(
    api_client: AsyncClient,
    initialized_system,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_ensure_backup_folder(monkeypatch)
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)

    backup_response = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    assert backup_response.status_code == 200
    filename = backup_response.json()["data"]["filename"]

    connect_response = await api_client.post(
        "/api/v1/settings/backups/cloud/google-drive/connect",
        headers=headers,
        json={"refresh_token": "fake-refresh-token", "account_email": "shop@example.com"},
    )
    assert connect_response.status_code == 200

    disconnect_response = await api_client.post(
        "/api/v1/settings/backups/cloud/google-drive/disconnect",
        headers=headers,
    )
    assert disconnect_response.status_code == 200
    assert disconnect_response.json()["data"]["connected"] is False

    history_response = await api_client.get(
        "/api/v1/settings/backups/admin/history",
        headers=headers,
    )
    assert history_response.status_code == 200
    items = history_response.json()["data"]
    assert any(item["filename"] == filename for item in items)


@pytest.mark.asyncio
async def test_retention_update_requires_connection(
    api_client: AsyncClient,
    initialized_system,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    response = await api_client.patch(
        "/api/v1/settings/backups/cloud/retention",
        headers=headers,
        json={"retention_count": 40},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_retention_update_after_connect(
    api_client: AsyncClient,
    initialized_system,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_ensure_backup_folder(monkeypatch)
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    await api_client.post(
        "/api/v1/settings/backups/cloud/google-drive/connect",
        headers=headers,
        json={"refresh_token": "fake-refresh-token", "account_email": "shop@example.com"},
    )
    response = await api_client.patch(
        "/api/v1/settings/backups/cloud/retention",
        headers=headers,
        json={"retention_count": 40},
    )
    assert response.status_code == 200
    assert response.json()["data"]["retention_count"] == 40


async def _create_connection(
    db_session: AsyncSession,
    test_settings: Settings,
    *,
    status: str = "connected",
    retention_count: int = 25,
) -> None:
    connections = CloudBackupConnectionRepository(db_session)
    record = await connections.upsert_connected(
        provider=GOOGLE_DRIVE_PROVIDER,
        account_email="shop@example.com",
        encrypted_refresh_token=encrypt_secret(
            "fake-refresh-token", secret=test_settings.jwt_secret
        ),
        drive_folder_id="folder-1",
        connected_by_user_id=None,
    )
    record.status = status
    record.retention_count = retention_count
    await db_session.flush()
    await db_session.commit()


async def _create_completed_run(db_session: AsyncSession, *, filename: str) -> int:
    runs = BackupRunRepository(db_session)
    run = await runs.create_run(
        filename=filename,
        archive_path=f"/tmp/{filename}",
        backup_type="full",
        trigger_type="manual",
        storage_backend="google_drive",
        creator_user_id=None,
        creator_display_name="Test",
    )
    completed = await runs.mark_completed(
        run,
        size_bytes=1024,
        duration_ms=10,
        checksum_sha256="deadbeef",
        schema_version="1",
        app_version="0.1.0",
        verification_status="success",
        warnings=[],
        errors=[],
        manifest={},
    )
    await db_session.commit()
    return completed.id


@pytest.mark.asyncio
async def test_scheduler_uploads_pending_backup(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create_connection(db_session, test_settings)
    run_id = await _create_completed_run(db_session, filename="cloud-upload-success.tar.gz")

    monkeypatch.setattr(GoogleDriveClient, "upload_file", lambda self, **kwargs: "drive-file-id-1")
    monkeypatch.setattr(GoogleDriveClient, "list_files_oldest_first", lambda self, **kwargs: [])

    await run_cloud_backup_sync(db_session, test_settings)

    runs = BackupRunRepository(db_session)
    refreshed = await runs.get_by_id(run_id)
    assert refreshed is not None
    assert refreshed.cloud_upload_status == "uploaded"
    assert refreshed.cloud_file_id == "drive-file-id-1"
    assert refreshed.cloud_uploaded_at is not None


@pytest.mark.asyncio
async def test_scheduler_upload_failure_does_not_raise(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create_connection(db_session, test_settings)
    run_id = await _create_completed_run(db_session, filename="cloud-upload-failure.tar.gz")

    def _boom(self, **kwargs):
        raise GoogleDriveError("simulated network failure")

    monkeypatch.setattr(GoogleDriveClient, "upload_file", _boom)
    monkeypatch.setattr(GoogleDriveClient, "list_files_oldest_first", lambda self, **kwargs: [])

    await run_cloud_backup_sync(db_session, test_settings)

    runs = BackupRunRepository(db_session)
    refreshed = await runs.get_by_id(run_id)
    assert refreshed is not None
    assert refreshed.cloud_upload_status == "failed"


@pytest.mark.asyncio
async def test_scheduler_retention_deletes_oldest_beyond_count(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create_connection(db_session, test_settings, retention_count=3)

    files = [{"id": f"file-{i}", "name": f"backup-{i}.tar.gz"} for i in range(5)]
    deleted_ids: list[str] = []

    monkeypatch.setattr(GoogleDriveClient, "list_files_oldest_first", lambda self, **kwargs: files)
    monkeypatch.setattr(
        GoogleDriveClient,
        "delete_file",
        lambda self, *, file_id: deleted_ids.append(file_id),
    )

    await run_cloud_backup_sync(db_session, test_settings)

    assert deleted_ids == ["file-0", "file-1"]


@pytest.mark.asyncio
async def test_scheduler_auth_error_sets_connection_error_status(
    db_session: AsyncSession,
    test_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _create_connection(db_session, test_settings)

    def _revoked(self):
        raise drive_client_module.GoogleDriveAuthError("invalid_grant")

    monkeypatch.setattr(GoogleDriveClient, "ensure_backup_folder", _revoked)

    connections = CloudBackupConnectionRepository(db_session)
    connection = await connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
    connection.drive_folder_id = None
    await db_session.flush()

    await run_cloud_backup_sync(db_session, test_settings)

    refreshed = await connections.get_by_provider(GOOGLE_DRIVE_PROVIDER)
    assert refreshed is not None
    assert refreshed.status == "error"
    assert refreshed.last_error


@pytest.mark.asyncio
async def test_scheduler_noop_when_not_connected(
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    # No connection row exists at all — must be a complete no-op, no exception.
    await run_cloud_backup_sync(db_session, test_settings)
    assert scheduler_module.CLOUD_SYNC_POLL_INTERVAL_SECONDS == 900
