"""Tests for Tally GST amount helpers."""

from __future__ import annotations

from webstudio_backend.integrations.tally.gst import (
    resolve_line_sale_amounts,
    split_sale_amount_with_gst,
)


def test_split_sale_amount_with_gst_applies_eighteen_percent() -> None:
    exclusive, inclusive = split_sale_amount_with_gst(125000.0)
    assert exclusive == 125000.0
    assert inclusive == 147500.0


def test_split_sale_amount_with_gst_none() -> None:
    assert split_sale_amount_with_gst(None) == (None, None)


def test_resolve_line_sale_amounts_without_gst_breakdown() -> None:
    from webstudio_backend.integrations.tally.types import TallyInventoryLine

    line = TallyInventoryLine(
        line_index=0,
        stock_item_name="Laptop",
        quantity="1",
        serial_number="SN1",
        amount="125000.00",
        line_total="125000.00",
    )
    assert resolve_line_sale_amounts(line) == (None, 125000.0)


def test_resolve_line_sale_amounts_with_line_gst() -> None:
    from webstudio_backend.integrations.tally.types import TallyInventoryLine

    line = TallyInventoryLine(
        line_index=0,
        stock_item_name="Laptop",
        quantity="1",
        serial_number="SN1",
        amount="100000.00",
        taxable_amount="100000.00",
        cgst_amount="9000.00",
        sgst_amount="9000.00",
        line_total="100000.00",
    )
    assert resolve_line_sale_amounts(line) == (100000.0, 118000.0)
