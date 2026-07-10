"""Parsed Tally voucher structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TallyInventoryLine:
    line_index: int
    stock_item_name: str
    quantity: str
    serial_number: str | None
    batch_allocations: list[str] = field(default_factory=list)
    amount: str | None = None
    rate: str | None = None
    taxable_amount: str | None = None
    cgst_amount: str | None = None
    sgst_amount: str | None = None
    igst_amount: str | None = None
    cess_amount: str | None = None
    line_total: str | None = None
    serial_source: str | None = None
    normalized_serial: str | None = None


@dataclass(frozen=True, slots=True)
class TallyVoucherTotals:
    subtotal: Decimal | None = None
    discount_amount: Decimal | None = None
    round_off: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    cess_amount: Decimal | None = None
    grand_total: Decimal | None = None


@dataclass(frozen=True, slots=True)
class TallyVoucher:
    guid: str
    master_id: str | None
    voucher_type: str
    voucher_number: str
    printed_invoice_number: str
    voucher_date: date
    party_name: str | None
    narration: str | None
    inventory_lines: list[TallyInventoryLine]
    payment_mode: str | None = None
    amount: str | None = None
    totals: TallyVoucherTotals = field(default_factory=TallyVoucherTotals)
    raw_xml: str | None = None
