"""GST helpers for Tally sale amounts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucherTotals

GST_RATE = Decimal("0.18")


@dataclass(frozen=True, slots=True)
class LineGstBreakdown:
    base_excluding_gst: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    cess_amount: float
    amount_including_gst: float


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


def allocate_voucher_gst_to_line(
    inclusive: float | None, voucher_totals: TallyVoucherTotals
) -> LineGstBreakdown | None:
    """Split a line's known GST-inclusive amount into base + CGST/SGST/IGST/cess
    using the VOUCHER's own effective tax rate and component ratio.

    Tally almost always records GST as separate ledger entries at the voucher
    level rather than per stock item, so an individual line's own tax fields
    are typically empty (see ``resolve_line_sale_amounts``). Rather than show
    no breakdown at all, derive this invoice's effective rate (total tax /
    taxable subtotal) and apply it to this line's own inclusive amount,
    splitting the resulting tax in the same CGST:SGST:IGST:cess proportion as
    the invoice's own totals. This keeps the line's already-known inclusive
    total exact and distributes tax proportionally across multi-item invoices
    instead of assuming every line carries an equal share.
    """
    if inclusive is None:
        return None
    subtotal = voucher_totals.subtotal
    if not subtotal or subtotal <= 0:
        return None

    inc = Decimal(str(inclusive)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    voucher_cgst = voucher_totals.cgst_amount or Decimal("0")
    voucher_sgst = voucher_totals.sgst_amount or Decimal("0")
    voucher_igst = voucher_totals.igst_amount or Decimal("0")
    voucher_cess = voucher_totals.cess_amount or Decimal("0")
    voucher_tax = voucher_cgst + voucher_sgst + voucher_igst + voucher_cess
    if voucher_tax <= 0:
        return LineGstBreakdown(
            base_excluding_gst=float(inc),
            cgst_amount=0.0,
            sgst_amount=0.0,
            igst_amount=0.0,
            cess_amount=0.0,
            amount_including_gst=float(inc),
        )

    rate = voucher_tax / subtotal
    base = (inc / (Decimal("1") + rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    line_tax = (inc - base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _share(component: Decimal) -> Decimal:
        return (line_tax * component / voucher_tax).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return LineGstBreakdown(
        base_excluding_gst=float(base),
        cgst_amount=float(_share(voucher_cgst)),
        sgst_amount=float(_share(voucher_sgst)),
        igst_amount=float(_share(voucher_igst)),
        cess_amount=float(_share(voucher_cess)),
        amount_including_gst=float(inc),
    )
