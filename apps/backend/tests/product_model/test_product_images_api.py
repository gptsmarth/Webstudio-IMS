"""Product image proxy API tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import StorageType, StorageUnit
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)


def _real_png_bytes() -> bytes:
    """A PNG large enough to pass the tiny-image (tracking pixel) guard."""
    import io

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (200, 200), color=(30, 60, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


_PNG_BYTES = _real_png_bytes()


@pytest.mark.asyncio
async def test_product_image_proxy_requires_auth(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
) -> None:
    managed_url = "/assets/product-images/missing-test-image.jpg"

    unauth = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": managed_url},
    )
    assert unauth.status_code == 401

    authed = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": managed_url},
        headers=salesperson_headers,
    )
    assert authed.status_code == 404


@pytest.mark.asyncio
async def test_proxy_serves_webp_with_explicit_content_type(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows MIME maps often omit webp; the proxy must still return image/webp."""
    from webstudio_backend.api.routers import product_images as module

    assets = tmp_path / "assets"
    (assets / "product-images").mkdir(parents=True)
    webp_path = assets / "product-images" / "sample.webp"
    # Minimal RIFF/WEBP header is enough for content-type routing tests.
    webp_bytes = b"RIFF\x00\x00\x00\x00WEBP" + (_PNG_BYTES[:64])
    webp_path.write_bytes(webp_bytes)
    monkeypatch.setattr(module, "managed_asset_search_dirs", lambda: [assets])

    response = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": "/assets/product-images/sample.webp"},
        headers=salesperson_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.content == webp_bytes


@pytest.mark.asyncio
async def test_proxy_serves_asset_from_any_search_dir(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Files written under an older storage location must still be served —
    the proxy searches every known managed-assets directory."""
    from webstudio_backend.api.routers import product_images as module

    primary = tmp_path / "data-root" / "assets"
    legacy = tmp_path / "repo" / "assets"
    (legacy / "product-images").mkdir(parents=True)
    (legacy / "product-images" / "legacy-image.png").write_bytes(_PNG_BYTES)
    primary.mkdir(parents=True)

    monkeypatch.setattr(module, "managed_asset_search_dirs", lambda: [primary, legacy])

    response = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": "/assets/product-images/legacy-image.png"},
        headers=salesperson_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == _PNG_BYTES


@pytest.mark.asyncio
async def test_proxy_missing_managed_image_self_heals(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
    db_session: AsyncSession,
    brand: Brand,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A dead `/assets/product-images/{model_id}.*` link clears the stored URL
    and schedules background re-discovery, so the image repairs itself."""
    from webstudio_backend.api.routers import product_images as module

    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand.id,
        model_number="HEAL-TEST-01",
        model_name="Heal Test",
        cpu="Intel Core i5",
        gpu="Intel Iris Xe",
        ram_gb=8,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    dead_url = f"/assets/product-images/{model.id}.webp"
    model.product_image_url = dead_url
    await db_session.commit()

    empty_dir = tmp_path / "assets"
    empty_dir.mkdir(parents=True)
    monkeypatch.setattr(module, "managed_asset_search_dirs", lambda: [empty_dir])

    scheduled: list[str] = []
    monkeypatch.setattr(
        module,
        "schedule_product_image_resolve",
        lambda model_id, force=False: scheduled.append(str(model_id)) or True,
    )

    response = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": dead_url},
        headers=salesperson_headers,
    )
    assert response.status_code == 404

    await db_session.refresh(model)
    assert model.product_image_url is None
    assert scheduled == [str(model.id)]


@pytest.mark.asyncio
async def test_proxy_junk_pixel_image_is_deleted_and_healed(
    api_client: AsyncClient,
    salesperson_headers: dict[str, str],
    db_session: AsyncSession,
    brand: Brand,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Stored 8x8 tracking pixels (saved by older scraper versions) are treated
    as missing: the file is deleted, the URL cleared, and re-discovery queued."""
    import io

    from PIL import Image

    from webstudio_backend.api.routers import product_images as module

    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand.id,
        model_number="JUNK-PIXEL-01",
        model_name="Junk Pixel Test",
        cpu="Intel Core i5",
        gpu="Intel Iris Xe",
        ram_gb=8,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    junk_url = f"/assets/product-images/{model.id}.jpg"
    model.product_image_url = junk_url
    await db_session.commit()

    assets_dir = tmp_path / "assets"
    (assets_dir / "product-images").mkdir(parents=True)
    junk_file = assets_dir / "product-images" / f"{model.id}.jpg"
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="JPEG")
    junk_file.write_bytes(buffer.getvalue())

    monkeypatch.setattr(module, "managed_asset_search_dirs", lambda: [assets_dir])
    scheduled: list[str] = []
    monkeypatch.setattr(
        module,
        "schedule_product_image_resolve",
        lambda model_id, force=False: scheduled.append(str(model_id)) or True,
    )

    response = await api_client.get(
        "/api/v1/product-images/proxy",
        params={"url": junk_url},
        headers=salesperson_headers,
    )
    assert response.status_code == 404
    assert not junk_file.exists()

    await db_session.refresh(model)
    assert model.product_image_url is None
    assert scheduled == [str(model.id)]
