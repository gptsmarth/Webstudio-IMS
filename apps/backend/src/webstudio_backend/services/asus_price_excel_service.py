"""ASUS live price manual spreadsheet.

Gemini search-grounding can't always be trusted for ASUS pricing (renewed/
refurbished listings, stale or ambiguous search results) — this gives the
admin a reliable manual fallback for exactly the models that matter right
now: download a template of every in-stock ASUS laptop, look each one up on
the ASUS website by hand, fill in the price column, and re-upload it to
apply those prices in bulk. Every applied price is recorded the same way as
a single manual edit (`ProductModelRepository.set_manual_live_price`) — no
separate "came from a spreadsheet" status is kept; it's just the ASUS live
price, same as any other source.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from openpyxl import Workbook, load_workbook
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)

_SHEET_TITLE = "ASUS Live Prices"
_HEADER_MODEL_NUMBER = "Model Number"
_HEADER_PRICE = "ASUS Live Price"

TEMPLATE_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TEMPLATE_FILENAME = "asus-live-price-template.xlsx"


async def build_asus_price_template(session: AsyncSession) -> bytes:
    """One row per active, in-stock ASUS laptop: model number + its current
    live price (pre-filled for reference, blank if never resolved) so the
    admin can spot and correct wrong values rather than starting from
    scratch. Zero-stock models are left out — nothing to sell, nothing to
    price."""
    models = await ProductModelRepository(session).list_asus_laptops_with_stock()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = _SHEET_TITLE[:31]
    worksheet.append([_HEADER_MODEL_NUMBER, _HEADER_PRICE])
    for pm in models:
        worksheet.append(
            [pm.model_number, float(pm.live_price) if pm.live_price is not None else None]
        )
    worksheet.column_dimensions["A"].width = 30
    worksheet.column_dimensions["B"].width = 18
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@dataclass
class AsusPriceImportResult:
    updated: int = 0
    cleared: int = 0
    not_matched: list[str] = field(default_factory=list)
    invalid_rows: list[str] = field(default_factory=list)


def _find_column(header_row, *, wanted: str) -> int | None:
    for idx, cell in enumerate(header_row):
        if str(cell.value or "").strip().lower() == wanted.lower():
            return idx
    return None


def _parse_price(raw: object) -> Decimal | None:
    """Tolerates the messy real-world formatting of a hand-filled cell —
    currency symbols, thousands separators, trailing whitespace.

    Returns None for a blank cell or an explicit zero/negative value — both
    mean "no price / NA", exactly like leaving a model unpriced. Raises
    ValueError only for text that isn't numeric at all (a real data-entry
    mistake, reported back rather than silently cleared).
    """
    if raw is None:
        return None
    if isinstance(raw, int | float | Decimal):
        try:
            value = Decimal(str(raw))
        except InvalidOperation as exc:
            raise ValueError(str(raw)) from exc
        return value if value > 0 else None
    text = str(raw).strip()
    if not text:
        return None
    cleaned = re.sub(r"[^\d.]", "", text)
    if not cleaned:
        raise ValueError(text)
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(text) from exc
    return value if value > 0 else None


async def import_asus_price_sheet(session: AsyncSession, content: bytes) -> AsusPriceImportResult:
    """Apply prices from an uploaded copy of the template. Matches rows by
    exact (trimmed, case-insensitive) model number against every active
    ASUS laptop — not just currently in-stock ones, since stock may have
    changed between download and re-upload.

    A blank price cell, or an explicit 0, clears that model's live price to
    NA rather than being skipped — the admin can deliberately blank out a
    wrong pre-filled price (or type 0) to mark "not available", and the
    software should actually reflect that. Only genuinely non-numeric text
    is reported back as invalid and left untouched.
    """
    try:
        workbook = load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    except Exception as exc:
        raise ValueError("Could not read this file as an Excel spreadsheet.") from exc

    worksheet = workbook.active
    if worksheet is None:
        raise ValueError("The spreadsheet has no sheets.")
    rows_iter = worksheet.iter_rows()
    try:
        header_row = next(rows_iter)
    except StopIteration as exc:
        raise ValueError("The spreadsheet is empty.") from exc

    model_col = _find_column(header_row, wanted=_HEADER_MODEL_NUMBER)
    price_col = _find_column(header_row, wanted=_HEADER_PRICE)
    if model_col is None or price_col is None:
        raise ValueError(
            f'Expected columns "{_HEADER_MODEL_NUMBER}" and "{_HEADER_PRICE}" — '
            "use the downloaded template without renaming the header row."
        )

    repo = ProductModelRepository(session)
    by_model_number = await repo.map_active_asus_laptops_by_model_number()

    result = AsusPriceImportResult()
    for row in rows_iter:
        raw_model = row[model_col].value if model_col < len(row) else None
        model_number = str(raw_model).strip() if raw_model is not None else ""
        if not model_number:
            continue

        raw_price = row[price_col].value if price_col < len(row) else None
        try:
            price = _parse_price(raw_price)
        except ValueError:
            result.invalid_rows.append(model_number)
            continue

        product_model = by_model_number.get(model_number.strip().upper())
        if product_model is None:
            result.not_matched.append(model_number)
            continue

        await repo.set_manual_live_price(product_model, price=price)
        if price is None:
            result.cleared += 1
        else:
            result.updated += 1

    await session.commit()
    return result
