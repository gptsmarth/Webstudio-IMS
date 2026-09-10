"""Purchase Import: ignore (tombstone) + historical backfill (additive feature).

Proves an ignored voucher disappears from the default queue but is retained
(so the next sync will not re-add it), and that backfill is gated on Tally being
enabled.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)

pytestmark = pytest.mark.asyncio


async def test_ignore_hides_voucher_from_default_queue(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    # Present before ignoring.
    before = await api_client.get("/api/v1/purchase/queue", headers=main_admin_headers)
    assert before.status_code == 200
    assert len(before.json()["data"]) == 1

    ignored = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/ignore",
        headers=main_admin_headers,
    )
    assert ignored.status_code == 200, ignored.text
    assert ignored.json()["data"]["status"] == "ignored"

    # Gone from the default queue …
    after = await api_client.get("/api/v1/purchase/queue", headers=main_admin_headers)
    assert after.status_code == 200
    assert after.json()["data"] == []

    # … but retained (visible when explicitly filtering, detail still resolves).
    filtered = await api_client.get(
        "/api/v1/purchase/queue",
        headers=main_admin_headers,
        params={"status": "ignored"},
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["data"]) == 1

    detail = await api_client.get(
        f"/api/v1/purchase/queue/{purchase_voucher.id}", headers=main_admin_headers
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["status"] == "ignored"


async def test_ignore_is_idempotent(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    first = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/ignore", headers=main_admin_headers
    )
    assert first.status_code == 200
    second = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/ignore", headers=main_admin_headers
    )
    assert second.status_code == 200
    assert second.json()["data"]["status"] == "ignored"


async def test_ignore_blocked_when_fully_imported(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    laptop = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS F1504FA-BQ2113WS",
            "brand_id": brand.id,
            "mode": "existing",
            "product_model_id": str(product_model.id),
            "serial_numbers": ["SNPUR001", "SNPUR002"],
            "color": "Black",
            "current_location_id": location.id,
        },
    )
    assert laptop.status_code == 200, laptop.text

    accessory = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS Carry Case",
            "brand_id": brand.id,
            "mode": "new",
            "new_product_model": {
                "brand_id": brand.id,
                "model_number": "CARRY-CASE-01",
                "model_name": "ASUS Carry Case",
                "cpu": "N/A",
                "ram_gb": 1,
                "storage_value": 1,
                "storage_unit": "GB",
                "storage_type": "SSD",
            },
            "serial_numbers": ["ACC001", "ACC002"],
            "color": "Black",
            "current_location_id": location.id,
        },
    )
    assert accessory.status_code == 200, accessory.text

    blocked = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/ignore", headers=main_admin_headers
    )
    assert blocked.status_code == 409


async def test_ignore_missing_voucher_returns_404(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/queue/999999/ignore", headers=main_admin_headers
    )
    assert response.status_code == 404


async def test_mark_imported_closes_voucher_with_lines_left_out(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    # Only import the laptop group — leave the accessory group untouched.
    laptop = await api_client.post(
        "/api/v1/purchase/import",
        headers=main_admin_headers,
        json={
            "voucher_id": purchase_voucher.id,
            "group_key": "ASUS F1504FA-BQ2113WS",
            "brand_id": brand.id,
            "mode": "existing",
            "product_model_id": str(product_model.id),
            "serial_numbers": ["SNPUR101", "SNPUR102"],
            "color": "Black",
            "current_location_id": location.id,
        },
    )
    assert laptop.status_code == 200, laptop.text

    detail = await api_client.get(
        f"/api/v1/purchase/queue/{purchase_voucher.id}", headers=main_admin_headers
    )
    assert detail.json()["data"]["status"] == "partially_imported"

    closed = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/mark-imported",
        headers=main_admin_headers,
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["data"]["status"] == "imported"

    # An "Imported" voucher — manual or organic — is hidden from the default
    # ("All") queue, same as Ignored.
    default_queue = await api_client.get("/api/v1/purchase/queue", headers=main_admin_headers)
    assert default_queue.json()["data"] == []

    imported_queue = await api_client.get(
        "/api/v1/purchase/queue",
        headers=main_admin_headers,
        params={"status": "imported"},
    )
    assert len(imported_queue.json()["data"]) == 1

    # Status stays Imported — not recomputed back to partially_imported — even
    # though the accessory group was never actually imported.
    after = await api_client.get(
        f"/api/v1/purchase/queue/{purchase_voucher.id}", headers=main_admin_headers
    )
    assert after.json()["data"]["status"] == "imported"


async def test_mark_imported_is_idempotent(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    first = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/mark-imported",
        headers=main_admin_headers,
    )
    assert first.status_code == 200
    second = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/mark-imported",
        headers=main_admin_headers,
    )
    assert second.status_code == 200
    assert second.json()["data"]["status"] == "imported"


async def test_mark_imported_blocked_when_ignored(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
    purchase_voucher: TallyPurchaseVoucher,
) -> None:
    ignored = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/ignore", headers=main_admin_headers
    )
    assert ignored.status_code == 200

    blocked = await api_client.post(
        f"/api/v1/purchase/queue/{purchase_voucher.id}/mark-imported",
        headers=main_admin_headers,
    )
    assert blocked.status_code == 409


async def test_mark_imported_missing_voucher_returns_404(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    response = await api_client.post(
        "/api/v1/purchase/queue/999999/mark-imported", headers=main_admin_headers
    )
    assert response.status_code == 404


async def test_backfill_requires_tally_enabled(
    api_client: AsyncClient,
    main_admin_headers: dict[str, str],
) -> None:
    # Tally is disabled by default in the test system settings.
    response = await api_client.post(
        "/api/v1/purchase/backfill",
        headers=main_admin_headers,
        json={"from_date": "2025-06-01"},
    )
    assert response.status_code == 409
