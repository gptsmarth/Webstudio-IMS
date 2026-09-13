"""ASUS live price manual spreadsheet — download template + re-upload import.

Exists as a reliable fallback to the automatic Gemini search (which can pull
a wrong, e.g. refurbished, price): the admin downloads a spreadsheet of
in-stock ASUS laptops, fills in prices by hand from the ASUS website, and
re-uploads it to apply them in bulk.
"""

from __future__ import annotations

import io
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from openpyxl import Workbook, load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    StorageType,
    StorageUnit,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.asus_price_excel_service import (
    build_asus_price_template,
    import_asus_price_sheet,
)


async def _make_model(db_session: AsyncSession, brand_id: int, model_number: str):
    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand_id,
        model_number=model_number,
        model_name="Test Laptop",
        cpu="Intel",
        gpu="Intel",
        ram_gb=8,
        storage_value=Decimal("256"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )
    await db_session.commit()
    return model


async def _add_available_unit(db_session: AsyncSession, product_model_id: uuid.UUID) -> None:
    location = await LocationRepository(db_session).create(
        f"Test Location {uuid.uuid4().hex[:8]}", location_type=LocationType.WAREHOUSE
    )
    await db_session.commit()
    await InventoryItemRepository(db_session).create(
        serial_number=f"SN-{uuid.uuid4().hex[:10].upper()}",
        product_model_id=product_model_id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()


def _read_rows(content: bytes) -> list[tuple]:
    workbook = load_workbook(io.BytesIO(content))
    worksheet = workbook.active
    return [tuple(cell.value for cell in row) for row in worksheet.iter_rows()]


def _build_upload(rows: list[tuple[str, object]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Model Number", "ASUS Live Price"])
    for model_number, price in rows:
        worksheet.append([model_number, price])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_template_only_includes_in_stock_asus_laptops(
    db_session: AsyncSession, test_settings, brand
) -> None:
    in_stock = await _make_model(db_session, brand.id, "ASUS-T-001")
    await _add_available_unit(db_session, in_stock.id)
    await _make_model(db_session, brand.id, "ASUS-T-002")

    content = await build_asus_price_template(db_session)
    rows = _read_rows(content)

    assert rows[0] == ("Model Number", "ASUS Live Price")
    model_numbers = [row[0] for row in rows[1:]]
    assert "ASUS-T-001" in model_numbers
    assert "ASUS-T-002" not in model_numbers


@pytest.mark.asyncio
async def test_template_prefills_current_price_for_reference(
    db_session: AsyncSession, test_settings, brand
) -> None:
    repo = ProductModelRepository(db_session)
    model = await _make_model(db_session, brand.id, "ASUS-T-003")
    await _add_available_unit(db_session, model.id)
    await repo.set_manual_live_price(model, price=Decimal("54999"))
    await db_session.commit()

    content = await build_asus_price_template(db_session)
    rows = _read_rows(content)
    row = next(r for r in rows[1:] if r[0] == "ASUS-T-003")
    assert row[1] == 54999.0


@pytest.mark.asyncio
async def test_import_applies_prices_to_matching_models(
    db_session: AsyncSession, test_settings, brand
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-T-010")
    upload = _build_upload([("ASUS-T-010", 61990)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 1
    assert result.not_matched == []
    assert result.invalid_rows == []
    await db_session.refresh(model)
    assert model.live_price == Decimal("61990")
    assert model.live_price_status == "manual"
    assert model.live_price_source_url is None


@pytest.mark.asyncio
async def test_import_matches_model_number_case_insensitively_and_trimmed(
    db_session: AsyncSession, test_settings, brand
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-T-011")
    upload = _build_upload([("  asus-t-011  ", 47999)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 1
    await db_session.refresh(model)
    assert model.live_price == Decimal("47999")


@pytest.mark.asyncio
async def test_import_tolerates_currency_symbols_and_commas(
    db_session: AsyncSession, test_settings, brand
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-T-012")
    upload = _build_upload([("ASUS-T-012", "₹1,04,990.00")])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 1
    await db_session.refresh(model)
    assert model.live_price == Decimal("104990.00")


@pytest.mark.asyncio
async def test_import_clears_price_to_na_on_a_blank_cell(
    db_session: AsyncSession, test_settings, brand
) -> None:
    """A blank price cell for a matched model clears it to NA rather than
    leaving the old (possibly wrong) price untouched — lets the admin
    deliberately blank out a pre-filled price to mark "not available"."""
    repo = ProductModelRepository(db_session)
    model = await _make_model(db_session, brand.id, "ASUS-T-013")
    await repo.set_manual_live_price(model, price=Decimal("39999"))
    await db_session.commit()
    upload = _build_upload([("ASUS-T-013", None)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 0
    assert result.cleared == 1
    await db_session.refresh(model)
    assert model.live_price is None
    assert model.live_price_status == "not_found"


@pytest.mark.asyncio
async def test_import_clears_price_to_na_on_an_explicit_zero(
    db_session: AsyncSession, test_settings, brand
) -> None:
    repo = ProductModelRepository(db_session)
    model = await _make_model(db_session, brand.id, "ASUS-T-013B")
    await repo.set_manual_live_price(model, price=Decimal("39999"))
    await db_session.commit()
    upload = _build_upload([("ASUS-T-013B", 0)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 0
    assert result.cleared == 1
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_import_blank_cell_for_an_unmatched_model_reports_not_matched(
    db_session: AsyncSession, test_settings, brand
) -> None:
    """Even a blank/clearing row still needs a real model match — an unknown
    model number is reported, not silently ignored or silently "cleared"."""
    upload = _build_upload([("NOT-A-REAL-MODEL", None)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.cleared == 0
    assert result.not_matched == ["NOT-A-REAL-MODEL"]


@pytest.mark.asyncio
async def test_import_reports_unmatched_model_numbers(
    db_session: AsyncSession, test_settings, brand
) -> None:
    upload = _build_upload([("NOT-A-REAL-MODEL", 12345)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 0
    assert result.not_matched == ["NOT-A-REAL-MODEL"]


@pytest.mark.asyncio
async def test_import_reports_invalid_price_values(
    db_session: AsyncSession, test_settings, brand
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-T-014")
    upload = _build_upload([("ASUS-T-014", "not a price")])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 0
    assert result.invalid_rows == ["ASUS-T-014"]
    await db_session.refresh(model)
    assert model.live_price is None


@pytest.mark.asyncio
async def test_import_does_not_match_zero_stock_models_out_of_scope(
    db_session: AsyncSession, test_settings, brand
) -> None:
    """Import matches against all active ASUS laptops (not just in-stock
    ones) — stock may have changed since the template was downloaded."""
    model = await _make_model(db_session, brand.id, "ASUS-T-015")
    upload = _build_upload([("ASUS-T-015", 59990)])

    result = await import_asus_price_sheet(db_session, upload)

    assert result.updated == 1
    await db_session.refresh(model)
    assert model.live_price == Decimal("59990")


@pytest.mark.asyncio
async def test_rejects_a_non_excel_file(db_session: AsyncSession, test_settings) -> None:
    with pytest.raises(ValueError):
        await import_asus_price_sheet(db_session, b"not an excel file")


@pytest.mark.asyncio
async def test_rejects_a_spreadsheet_missing_expected_columns(
    db_session: AsyncSession, test_settings
) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["Wrong Header", "Also Wrong"])
    worksheet.append(["X", 1])
    buffer = io.BytesIO()
    workbook.save(buffer)

    with pytest.raises(ValueError):
        await import_asus_price_sheet(db_session, buffer.getvalue())


@pytest.mark.asyncio
async def test_download_and_import_endpoints_are_settings_gated(
    api_client: AsyncClient,
    db_session: AsyncSession,
    main_admin_headers: dict[str, str],
    salesperson_headers: dict[str, str],
    brand,
) -> None:
    model = await _make_model(db_session, brand.id, "ASUS-T-020")
    await _add_available_unit(db_session, model.id)

    # Downloading (read-only) is available to anyone who can view Settings —
    # same "settings:view" tier as everything else on that page.
    resp = await api_client.get(
        "/api/v1/settings/integrations/asus-price-template", headers=salesperson_headers
    )
    assert resp.status_code == 200

    resp = await api_client.get(
        "/api/v1/settings/integrations/asus-price-template", headers=main_admin_headers
    )
    assert resp.status_code == 200
    rows = _read_rows(resp.content)
    assert rows[0] == ("Model Number", "ASUS Live Price")

    # Applying the uploaded prices is a write — "settings:modify" (Main Admin only).
    upload = _build_upload([("ASUS-T-020", 71990)])
    resp = await api_client.post(
        "/api/v1/settings/integrations/asus-price-import",
        headers=salesperson_headers,
        files={"file": ("prices.xlsx", upload)},
    )
    assert resp.status_code == 403

    resp = await api_client.post(
        "/api/v1/settings/integrations/asus-price-import",
        headers=main_admin_headers,
        files={"file": ("prices.xlsx", upload)},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["updated"] == 1
    await db_session.refresh(model)
    assert model.live_price == Decimal("71990")
