"""GST helpers for Tally sale amounts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucherTotals

GST_RATE = Decimal("0.18")
CENT = Decimal("0.01")
ZERO = Decimal("0.00")
GST_FIELDS = ("cgst_amount", "sgst_amount", "igst_amount", "cess_amount")


@dataclass(frozen=True, slots=True)
class LineGstBreakdown:
    base_excluding_gst: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    igst_amount: Decimal
    cess_amount: Decimal
    amount_including_gst: Decimal


def _money_decimal(value: str | Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        amount = Decimal(value)
        return amount.quantize(CENT, rounding=ROUND_HALF_UP) if amount.is_finite() else None
    except InvalidOperation:
        return None


def split_sale_amount_with_gst(exclusive: float | None) -> tuple[float | None, float | None]:
    """Return (excluding_gst, including_gst) from a Tally line amount."""
    if exclusive is None:
        return None, None

    ex = Decimal(str(exclusive)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    inc = (ex * (Decimal("1") + GST_RATE)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(ex), float(inc)


def resolve_line_sale_amounts(
    line: TallyInventoryLine, *, voucher_totals: TallyVoucherTotals | None = None
) -> tuple[float | None, float | None]:
    """Return (excluding_gst, including_gst) from a Tally inventory line.

    When the XML carries line-level GST fields, ``AMOUNT`` / ``TAXABLEAMOUNT`` is treated
    as exclusive and tax components are added for the inclusive total. When no GST breakdown
    is present, only the inclusive ``sale_amount`` is returned (exclusive stays ``None``).
    """
    gst = line_gst_breakdown(line)
    if voucher_totals is not None and not has_line_gst_details(line, voucher_totals):
        return float(gst.base_excluding_gst) if gst is not None else None, None
    if gst is not None:
        return float(gst.base_excluding_gst), float(gst.amount_including_gst)
    amount = _money_decimal(line.line_total or line.amount)
    return None, float(amount) if amount is not None else None


def has_line_gst_details(line: TallyInventoryLine, totals: TallyVoucherTotals) -> bool:
    return all(getattr(line, field) is not None for field in GST_FIELDS if getattr(totals, field))


def line_gst_breakdown(line: TallyInventoryLine) -> LineGstBreakdown | None:
    taxes = [_money_decimal(getattr(line, field)) for field in GST_FIELDS]
    if line.taxable_amount is None and all(tax is None for tax in taxes):
        return None
    base = _money_decimal(line.taxable_amount or line.amount or line.line_total)
    if base is None:
        return None
    cgst, sgst, igst, cess = (tax or ZERO for tax in taxes)
    return LineGstBreakdown(
        base,
        cgst,
        sgst,
        igst,
        cess,
        base + cgst + sgst + igst + cess,
    )


def apportion_money(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Allocate money by weight with a deterministic remainder in paise."""
    denominator = sum(weights, ZERO)
    if not denominator:
        if total:
            raise ValueError("Cannot allocate a nonzero amount without positive weights")
        return [ZERO] * len(weights)
    exact = [total * weight / denominator for weight in weights]
    amounts = [share.quantize(CENT, rounding=ROUND_DOWN) for share in exact]
    remaining = int((total - sum(amounts, ZERO)) / CENT)
    order = sorted(range(len(weights)), key=lambda i: exact[i] - amounts[i], reverse=True)
    for i in order[:remaining]:
        amounts[i] += CENT
    return amounts


def split_inventory_line(
    line: TallyInventoryLine, count: int, *, limit: int
) -> list[TallyInventoryLine]:
    """Split item amounts consistently across units without dropping paise."""
    if count <= 1:
        return [line]
    allocations = {}
    for field in ("amount", "taxable_amount", *GST_FIELDS, "line_total"):
        total = _money_decimal(getattr(line, field))
        if total is not None:
            allocations[field] = divmod(int(total / CENT), count)
    return [
        replace(
            line,
            quantity="1",
            **{
                key: str((paise + (i < remainder)) * CENT)
                for key, (paise, remainder) in allocations.items()
            },
        )
        for i in range(min(count, limit))
    ]


def _allocate_component(
    total: Decimal,
    known: list[Decimal | None],
    weights: list[Decimal],
    rates: list[Decimal | None],
) -> list[Decimal]:
    remaining = total - sum((amount for amount in known if amount is not None), ZERO)
    if remaining < ZERO:
        raise ValueError("Item GST exceeds the invoice tax ledger")
    missing = [i for i, amount in enumerate(known) if amount is None]
    exact = {i: weights[i] * rate / 100 for i in missing if (rate := rates[i]) is not None}
    rounded = {i: amount.quantize(CENT, rounding=ROUND_HALF_UP) for i, amount in exact.items()}
    without_rates = [i for i in missing if i not in rounded]
    if remaining == ZERO:
        estimates = dict.fromkeys(missing, ZERO)
    elif without_rates:
        remainder = remaining - sum(rounded.values(), ZERO)
        if remainder < ZERO:
            raise ValueError("Item GST rates exceed the invoice tax ledger")
        shares = apportion_money(remainder, [weights[i] for i in without_rates])
        estimates = rounded | dict(zip(without_rates, shares, strict=True))
    else:
        difference = remaining - sum(rounded.values(), ZERO)
        if abs(difference) > CENT * len(missing):
            raise ValueError("Item GST rates do not reconcile with the invoice tax ledger")
        estimates = (
            dict(zip(missing, apportion_money(remaining, [exact[i] for i in missing]), strict=True))
            if difference
            else rounded
        )
    return [estimates[i] if amount is None else amount for i, amount in enumerate(known)]


def reconcile_invoice_lines(
    lines: list[TallyInventoryLine], totals: TallyVoucherTotals
) -> tuple[list[TallyInventoryLine], TallyVoucherTotals]:
    """Use the invoice total to distinguish pre-tax and tax-inclusive item amounts."""
    if not lines:
        return lines, totals
    reported = [_money_decimal(line.amount or line.taxable_amount) for line in lines]
    if any(amount is None or amount < ZERO for amount in reported):
        return lines, totals
    amounts = [amount for amount in reported if amount is not None]
    base_candidates = [
        _money_decimal(line.taxable_amount) if line.taxable_amount is not None else amount
        for line, amount in zip(lines, amounts, strict=True)
    ]
    bases = [amount for amount in base_candidates if amount is not None and amount >= ZERO]
    if len(bases) != len(lines):
        return lines, totals

    recorded = {
        field: [_money_decimal(getattr(line, field)) for line in lines] for field in GST_FIELDS
    }
    tax_totals = {
        field: (
            getattr(totals, field)
            if getattr(totals, field) is not None
            else sum((tax for tax in taxes if tax is not None), ZERO)
        )
        for field, taxes in recorded.items()
    }
    total_tax = sum(tax_totals.values(), ZERO)
    round_off = totals.round_off or ZERO
    discount = totals.discount_amount or ZERO
    net_bill = totals.grand_total - round_off if totals.grand_total is not None else None
    basis: str | None = None
    applied_discount = ZERO
    for deduction in dict.fromkeys((discount, ZERO) if net_bill is None else (ZERO, discount)):
        if net_bill is None or sum(bases, ZERO) + total_tax - deduction == net_bill:
            basis, applied_discount = "exclusive", deduction
            break
        if total_tax > ZERO and sum(amounts, ZERO) - deduction == net_bill:
            basis, applied_discount = "inclusive", deduction
            break
    if basis is None:
        return lines, totals

    if total_tax == ZERO:
        subtotal = sum(bases, ZERO)
        return lines, replace(
            totals,
            subtotal=subtotal,
            discount_amount=applied_discount or None,
            grand_total=(
                totals.grand_total
                if totals.grand_total is not None
                else subtotal - applied_discount + round_off
            ),
        )

    allocated: dict[str, list[Decimal]] = {}
    weights = bases if basis == "exclusive" else amounts
    try:
        for field, taxes in recorded.items():
            allocated[field] = _allocate_component(
                tax_totals[field],
                taxes,
                weights,
                [line.gst_rates.get(field) if basis == "exclusive" else None for line in lines],
            )
    except ValueError:
        return lines, totals

    normalized: list[TallyInventoryLine] = []
    subtotal = ZERO
    for i, line in enumerate(lines):
        taxes = {field: values[i] for field, values in allocated.items()}
        tax = sum(taxes.values(), ZERO)
        base = bases[i] if basis == "exclusive" else amounts[i] - tax
        explicit_base = _money_decimal(line.taxable_amount)
        if base < ZERO or (explicit_base is not None and base != explicit_base):
            return lines, totals
        subtotal += base
        normalized.append(
            replace(
                line,
                taxable_amount=str(base),
                line_total=str(base + tax),
                gst_allocated=any(
                    recorded[field][i] is None and value != ZERO for field, value in taxes.items()
                ),
                **{field: str(value) for field, value in taxes.items()},
            )
        )
    return normalized, replace(
        totals,
        subtotal=subtotal,
        discount_amount=applied_discount or None,
        grand_total=(
            totals.grand_total
            if totals.grand_total is not None
            else subtotal + total_tax - applied_discount + round_off
        ),
        **{field: value or None for field, value in tax_totals.items()},
    )
