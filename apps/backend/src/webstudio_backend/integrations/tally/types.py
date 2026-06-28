"""Parsed Tally voucher structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True, slots=True)
class TallyInventoryLine:
    line_index: int
    stock_item_name: str
    quantity: str
    serial_number: str | None
    batch_allocations: list[str] = field(default_factory=list)


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
