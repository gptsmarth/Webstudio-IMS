"""GST helpers for Tally sale amounts."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from webstudio_backend.integrations.tally.types import TallyInventoryLine

GST_RATE = Decimal("0.18")


def _money_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def split_sale_amount_with_gst(exclusive: float | None) -> tuple[float | None, float | None]:
    """Return (excluding_gst, including_gst) from a Tally line amount."""
    if exclusive is None:
        return None, None

    ex = Decimal(str(exclusive)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inc = (ex * (Decimal("1") + GST_RATE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(ex), float(inc)


def resolve_line_sale_amounts(line: TallyInventoryLine) -> tuple[float | None, float | None]:
    """Return (excluding_gst, including_gst) from a Tally inventory line.

    When the XML carries line-level GST fields, ``AMOUNT`` / ``TAXABLEAMOUNT`` is treated
    as exclusive and tax components are added for the inclusive total. When no GST breakdown
    is present, only the inclusive ``sale_amount`` is returned (exclusive stays ``None``).
    """
    cgst = _money_decimal(line.cgst_amount) or Decimal("0")
    sgst = _money_decimal(line.sgst_amount) or Decimal("0")
    igst = _money_decimal(line.igst_amount) or Decimal("0")
    cess = _money_decimal(line.cess_amount) or Decimal("0")
    has_tax = any(amount > 0 for amount in (cgst, sgst, igst, cess)) or bool(line.taxable_amount)

    base = (
        _money_decimal(line.taxable_amount)
        or _money_decimal(line.amount)
        or _money_decimal(line.line_total)
    )
    if base is None:
        return None, None

    if not has_tax:
        return None, float(base)

    inclusive = (base + cgst + sgst + igst + cess).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(base), float(inclusive)
