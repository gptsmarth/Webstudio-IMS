"""Backup format detection and compatibility tests."""

from __future__ import annotations

# ruff: noqa: E402

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
from webstudio_backend.services.backup_format import (
    FORMAT_TAR_GZ,
    FORMAT_WSB,
    WSB_MAGIC,
    TarGzBackupLoader,
    WsbBackupLoader,
    detect_backup_format,
)
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


def test_detect_tar_gz_format(tmp_path: Path) -> None:
    payload = b"\x1f\x8b" + b"0" * 32
    archive = tmp_path / "webstudio-backup-test.tar.gz"
    archive.write_bytes(payload)
    assert isinstance(detect_backup_format(archive), TarGzBackupLoader)


def test_detect_wsb_format_by_extension(tmp_path: Path) -> None:
    payload = b"\x1f\x8b" + b"0" * 32
    archive = tmp_path / "export.wsb"
    archive.write_bytes(payload)
    loader = detect_backup_format(archive)
    assert isinstance(loader, WsbBackupLoader)
    assert loader.format_id == FORMAT_WSB


def test_detect_wsb_format_by_magic_header(tmp_path: Path) -> None:
    payload = WSB_MAGIC + b"\x1f\x8b" + b"0" * 32
    archive = tmp_path / "branded-backup.bin"
    archive.write_bytes(payload)
    loader = detect_backup_format(archive)
    assert loader.format_id == FORMAT_WSB


@pytest.mark.asyncio
async def test_validate_reports_backup_format(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    create = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    filename = create.json()["data"]["filename"]
    response = await api_client.post(
        "/api/v1/settings/backups/validate",
        headers=headers,
        json={"filename": filename, "source": "local"},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["backup_format_id"] == FORMAT_TAR_GZ
    assert payload["compatibility_report"]["backward_compatible"] is True

    backup_dir = await SettingsService(db_session, test_settings).get_backup_folder_path()
    restore = RestoreEngine(db_session, test_settings, backup_dir=backup_dir)
    validation = await restore.validate_backup(filename)
    assert validation.backup_format_id == FORMAT_TAR_GZ


@pytest.mark.asyncio
async def test_import_wsb_uses_same_restore_pipeline(
    api_client: AsyncClient,
    initialized_system,
    db_session: AsyncSession,
    test_settings: Settings,
) -> None:
    headers = await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)
    create = await api_client.post(
        "/api/v1/settings/backups",
        headers=headers,
        json={"backup_type": "full", "trigger_type": "manual"},
    )
    filename = create.json()["data"]["filename"]
    backup_dir = await SettingsService(db_session, test_settings).get_backup_folder_path()
    wsb_name = "webstudio-import-test.wsb"
    content = (backup_dir / filename).read_bytes()

    imported = await api_client.post(
        "/api/v1/settings/backups/import",
        headers=headers,
        files={"file": (wsb_name, content, "application/octet-stream")},
    )
    assert imported.status_code == 200
    payload = imported.json()["data"]
    assert payload["backup_format_id"] == FORMAT_WSB
    assert payload["filename"].endswith(".wsb")

    preview = await api_client.post(
        "/api/v1/settings/backups/preview",
        headers=headers,
        json={
            "filename": payload["filename"],
            "restore_scope": "settings_only",
            "source": "imported",
        },
    )
    assert preview.status_code == 200
    preview_body = preview.json()["data"]
    assert preview_body["backup_format_id"] == FORMAT_WSB
    assert preview_body["restore_allowed"] is True
