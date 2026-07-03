"""Product image upload validation tests."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image

from webstudio_backend.infrastructure.database.enums import StorageType, StorageUnit
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.product_image_service import validate_product_image_upload


def _jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="JPEG")
    return buffer.getvalue()


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="blue").save(buffer, format="PNG")
    return buffer.getvalue()


def test_validate_product_image_upload_accepts_valid_jpeg() -> None:
    payload = _jpeg_bytes()
    ext = validate_product_image_upload(
        filename="photo.jpg",
        content_type="image/jpeg",
        payload=payload,
    )
    assert ext == "jpg"


def test_validate_product_image_upload_rejects_invalid_magic_bytes() -> None:
    payload = b"MZ" + b"\x00" * 64
    with pytest.raises(ValueError, match="signature"):
        validate_product_image_upload(
            filename="photo.jpg",
            content_type="image/jpeg",
            payload=payload,
        )


def test_validate_product_image_upload_rejects_invalid_extension() -> None:
    payload = _jpeg_bytes()
    with pytest.raises(ValueError, match="extension"):
        validate_product_image_upload(
            filename="photo.exe",
            content_type="image/jpeg",
            payload=payload,
        )


def test_validate_product_image_upload_rejects_mime_extension_mismatch() -> None:
    payload = _png_bytes()
    with pytest.raises(ValueError, match="do not match"):
        validate_product_image_upload(
            filename="photo.png",
            content_type="image/jpeg",
            payload=payload,
        )


@pytest.mark.asyncio
async def test_product_image_upload_api_accepts_valid_image(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand,
    db_session,
) -> None:
    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand.id,
        model_number="UPLOAD-QA-001",
        model_name="Upload QA",
        cpu="Intel",
        gpu="Intel",
        ram_gb=8,
        storage_value=Decimal("256"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()

    payload = _jpeg_bytes()
    response = await api_client.post(
        "/api/v1/product-images/upload",
        headers=main_admin_headers,
        data={"product_model_id": str(model.id)},
        files={"file": ("laptop.jpg", payload, "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["product_image_url"].endswith(f"{model.id}.jpg")


@pytest.mark.asyncio
async def test_product_image_upload_api_rejects_invalid_magic_bytes(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand,
    db_session,
) -> None:
    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand.id,
        model_number="UPLOAD-QA-002",
        model_name="Upload QA Invalid",
        cpu="Intel",
        gpu="Intel",
        ram_gb=8,
        storage_value=Decimal("256"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()

    response = await api_client.post(
        "/api/v1/product-images/upload",
        headers=main_admin_headers,
        data={"product_model_id": str(model.id)},
        files={"file": ("laptop.jpg", b"MZ" + b"\x00" * 32, "image/jpeg")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
