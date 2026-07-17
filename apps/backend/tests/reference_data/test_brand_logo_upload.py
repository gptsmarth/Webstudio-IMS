"""Brand custom logo upload API tests (additive feature).

Reuses the same safe image validation as product image uploads and stores the
logo as a server-managed ``/assets/...`` asset served by the existing proxy.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from httpx import AsyncClient
from PIL import Image

import webstudio_backend.api.routers.brands as brands_router

pytestmark = pytest.mark.asyncio


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (12, 12), color="green").save(buffer, format="PNG")
    return buffer.getvalue()


async def _create_brand(api_client: AsyncClient, headers: dict[str, str], name: str) -> int:
    resp = await api_client.post("/api/v1/brands", json={"name": name}, headers=headers)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["data"]["id"]


async def test_upload_brand_logo_stores_managed_asset(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Redirect managed-asset storage to a temp dir so the repo tree stays clean.
    monkeypatch.setattr(brands_router, "resolve_managed_assets_dir", lambda **_: tmp_path)

    brand_id = await _create_brand(api_client, main_admin_headers, "LogoBrand")

    resp = await api_client.post(
        f"/api/v1/brands/{brand_id}/logo",
        headers=main_admin_headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["logo_filename"] == f"/assets/brand-logos/brand-{brand_id}.png"
    stored = tmp_path / "brand-logos" / f"brand-{brand_id}.png"
    assert stored.is_file()
    assert stored.read_bytes() == _png_bytes()


async def test_upload_brand_logo_rejects_non_image(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(brands_router, "resolve_managed_assets_dir", lambda **_: tmp_path)
    brand_id = await _create_brand(api_client, main_admin_headers, "BadLogoBrand")

    resp = await api_client.post(
        f"/api/v1/brands/{brand_id}/logo",
        headers=main_admin_headers,
        files={"file": ("evil.png", b"not an image", "image/png")},
    )
    assert resp.status_code == 400, resp.text


async def test_upload_brand_logo_requires_edit_permission(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(brands_router, "resolve_managed_assets_dir", lambda **_: tmp_path)
    brand_id = await _create_brand(api_client, main_admin_headers, "RbacLogoBrand")

    resp = await api_client.post(
        f"/api/v1/brands/{brand_id}/logo",
        headers=salesperson_headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 403, resp.text


async def test_upload_brand_logo_missing_brand_is_404(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(brands_router, "resolve_managed_assets_dir", lambda **_: tmp_path)
    resp = await api_client.post(
        "/api/v1/brands/999999/logo",
        headers=main_admin_headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 404, resp.text
