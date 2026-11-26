"""Backup format detection and compatibility tests."""

from __future__ import annotations

# ruff: noqa: E402

pytest_plugins = ["auth.conftest"]

import json
import tarfile
from collections.abc import AsyncGenerator
from io import BytesIO
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
from webstudio_backend.services.backup_manifest import (
    compatibility_report,
    compute_content_checksum,
)
from webstudio_backend.services.restore_engine import RestoreEngine
from webstudio_backend.services.settings_service import SettingsService


def _write_archive(path: Path, contents: list[tuple[str, bytes]]) -> None:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in contents:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, BytesIO(payload))


@pytest.mark.parametrize(
    "names",
    [
        ("assets/../../outside.txt",),
        (r"assets\product-images\outside.txt",),
        ("C:/outside.txt",),
        ("assets/product-images/CON.png",),
        ("assets/product-images/photo.png:other",),
        ("assets/product-images/Photo.png", "assets/product-images/photo.png"),
        ("assets/product-images/photo.png", "assets/product-images/photo.png"),
    ],
)
def test_rejects_unsafe_and_conflicting_archive_paths(
    tmp_path: Path, names: tuple[str, ...]
) -> None:
    archive = tmp_path / "backup.tar.gz"
    _write_archive(
        archive,
        [("manifest.json", b"{}"), ("database.sql", b"-- dump\n")]
        + [(name, b"image") for name in names],
    )
    workspace = tmp_path / "extracted"
    workspace.mkdir()
    result = detect_backup_format(archive).extract(archive, workspace)
    assert result.integrity_valid is False
    assert not list(workspace.iterdir())


def test_verifies_content_and_asset_digests(tmp_path: Path) -> None:
    archive = tmp_path / "backup.tar.gz"
    asset_file = "assets/product-images/product.png"
    asset_digest = "a" * 64
    files = [
        ("config/asset-manifest.json", json.dumps({"sha256": {asset_file: asset_digest}}).encode()),
        ("config/settings-registry.json", b"{}"),
        ("database.sql", b"-- fixture\n"),
    ]
    manifest = json.dumps(
        {
            "backup_version": "2.1",
            "checksum_algorithm": "sha256",
            "checksum": compute_content_checksum(*files),
        }
    ).encode()
    _write_archive(archive, [("manifest.json", manifest), *files, (asset_file, b"changed")])
    inspection = detect_backup_format(archive).inspect(archive)
    assert "A managed asset does not match its archive checksum." in inspection.errors[0]

    _write_archive(archive, [("manifest.json", manifest), *files[:2], ("database.sql", b"changed")])
    inspection = detect_backup_format(archive).inspect(archive)
    assert inspection.integrity_valid is False
    assert "content checksum does not match" in inspection.errors[0]


@pytest.mark.parametrize(
    ("schema", "allowed"),
    [
        ("0057_asus_live_price", True),
        ("0056_sale_gst_breakdown", False),
        ("0058_future", False),
        ("unknown", False),
    ],
)
def test_schema_revision_controls_compatibility(schema: str, allowed: bool) -> None:
    report = compatibility_report(
        {
            "app_version": "2.0.8",
            "schema_version": schema,
            "backup_version": "2.1",
            "database_dump_mode": "data_only",
        },
        current_app_version="2.6.0",
        current_schema_version="0057_asus_live_price",
        corruption_detected=False,
        integrity_valid=True,
    )
    assert report["app_version_match"] is False
    assert report["restore_allowed"] is allowed


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
