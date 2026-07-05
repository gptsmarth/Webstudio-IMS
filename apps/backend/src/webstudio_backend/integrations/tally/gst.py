"""GST helpers for Tally sale amounts."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

GST_RATE = Decimal("0.18")


def split_sale_amount_with_gst(exclusive: float | None) -> tuple[float | None, float | None]:
    """Return (excluding_gst, including_gst) from a Tally line amount."""
    if exclusive is None:
        return None, None

    ex = Decimal(str(exclusive)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inc = (ex * (Decimal("1") + GST_RATE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(ex), float(inc)
