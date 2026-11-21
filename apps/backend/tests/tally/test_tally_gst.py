"""Tests for Tally GST amount helpers."""

from __future__ import annotations

import gzip
from decimal import Decimal

from webstudio_backend.api.routers.sales import _present_invoice_amounts
from webstudio_backend.infrastructure.database.models.tally_processed_invoice import (
    TallyProcessedInvoice,
)
from webstudio_backend.infrastructure.database.models.tally_processed_invoice_line import (
    TallyProcessedInvoiceLine,
)
from webstudio_backend.integrations.tally.gst import (
    line_gst_breakdown,
    resolve_line_sale_amounts,
    split_sale_amount_with_gst,
)
from webstudio_backend.integrations.tally.xml_parser import (
    expand_inventory_lines,
    parse_vouchers_xml,
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


def _invoice_xml(
    items: list[tuple[str, str]],
    *,
    total: str,
    cgst: str,
    sgst: str,
    round_off: str | None = None,
) -> str:
    def ledger(name: str, amount: str) -> str:
        return (
            f"<LEDGERENTRIES.LIST><LEDGERNAME>{name}</LEDGERNAME>"
            f"<AMOUNT>{amount}</AMOUNT></LEDGERENTRIES.LIST>"
        )

    inventory = "".join(
        "<ALLINVENTORYENTRIES.LIST>"
        f"<STOCKITEMNAME>{name}</STOCKITEMNAME>{fields}"
        "</ALLINVENTORYENTRIES.LIST>"
        for name, fields in items
    )
    adjustments = ledger("Round Off", round_off) if round_off else ""
    return (
        "<VOUCHER><GUID>gst-test</GUID><VOUCHERTYPENAME>NEW SALE</VOUCHERTYPENAME>"
        "<DATE>20261031</DATE><PARTYLEDGERNAME>Customer</PARTYLEDGERNAME>"
        f"{ledger('Customer', '-' + total)}{ledger('CGST', cgst)}{ledger('SGST', sgst)}"
        f"{inventory}{adjustments}</VOUCHER>"
    )


def _rates(cgst: str, sgst: str) -> str:
    return "".join(
        f"<RATEDETAILS.LIST><GSTRATEDUTYHEAD>{head}</GSTRATEDUTYHEAD>"
        "<GSTRATEVALUATIONTYPE>Based on Value</GSTRATEVALUATIONTYPE>"
        f"<GSTRATE>{rate}</GSTRATE></RATEDETAILS.LIST>"
        for head, rate in (("CGST", cgst), ("SGST/UTGST", sgst))
    )


def test_archived_invoice_reconciles_printed_68000_bill_to_the_paisa() -> None:
    xml = _invoice_xml(
        [
            ("ASUS laptop", "<AMOUNT>56779.67</AMOUNT>" + _rates("9", "9")),
            ("ASUS backpack", "<AMOUNT>846.60</AMOUNT>" + _rates("9", "9")),
            ("Keyboard and mouse", "<AMOUNT>0.85</AMOUNT>" + _rates("9", "9")),
        ],
        total="68000.00",
        cgst="5186.44",
        sgst="5186.44",
    )
    archived = TallyProcessedInvoice(
        tally_voucher_guid="gst-test", raw_xml_gzip=gzip.compress(xml.encode())
    )
    processed = [
        TallyProcessedInvoiceLine(line_index=0, sale_id=1),
        TallyProcessedInvoiceLine(line_index=1, is_additional_product=True),
        TallyProcessedInvoiceLine(line_index=2, sale_id=2),
    ]
    totals, items = _present_invoice_amounts(archived, processed)

    assert totals.grand_total == Decimal("68000.00")
    assert totals.subtotal == Decimal("57627.12")
    assert [item.tracking for item in items] == ["tracked", "additional", "tracked"]
    for item, expected in zip(
        items,
        [
            ("56779.67", "5110.17", "67000.01"),
            ("846.60", "76.19", "998.98"),
            ("0.85", "0.08", "1.01"),
        ],
        strict=True,
    ):
        base, tax, gross = map(Decimal, expected)
        assert (item.amount_excluding_gst, item.cgst_amount, item.sgst_amount) == (base, tax, tax)
        assert item.amount_including_gst == gross


def test_item_rates_reconcile_different_tax_brackets_and_signed_round_off() -> None:
    xml = _invoice_xml(
        [
            ("Laptop", "<AMOUNT>100</AMOUNT>" + _rates("9", "9")),
            ("Bag", "<AMOUNT>50</AMOUNT>" + _rates("2.5", "2.5")),
        ],
        total="170.45",
        cgst="10.25",
        sgst="10.25",
        round_off="-0.05",
    )
    invoice = parse_vouchers_xml(xml)[0]
    assert invoice.totals.round_off == Decimal("-0.05")
    assert [resolve_line_sale_amounts(line) for line in invoice.inventory_lines] == [
        (100, 118),
        (50, 52.5),
    ]


def test_gst_inclusive_invoice_is_not_taxed_twice() -> None:
    xml = _invoice_xml(
        [
            (name, f"<AMOUNT>{amount}</AMOUNT>")
            for name, amount in [("Laptop", "47200"), ("Mouse", "1770"), ("Bag", "1030")]
        ],
        total="50000",
        cgst="3813.56",
        sgst="3813.56",
    )
    invoice = parse_vouchers_xml(xml)[0]
    assert [resolve_line_sale_amounts(line) for line in invoice.inventory_lines] == [
        (40000, 47200),
        (1500, 1770),
        (872.88, 1030),
    ]


def test_serialized_units_keep_all_paise() -> None:
    xml = _invoice_xml(
        [
            (
                "Laptop",
                "<AMOUNT>100</AMOUNT><ACTUALQTY>3 Nos</ACTUALQTY>"
                "<SERIALNUMBER>UNIT0001,UNIT0002,UNIT0003</SERIALNUMBER>",
            )
        ],
        total="118",
        cgst="9",
        sgst="9",
    )
    voucher = parse_vouchers_xml(xml)[0]
    lines = [line_gst_breakdown(line) for line in expand_inventory_lines(voucher.inventory_lines)]
    assert all(line is not None for line in lines)
    assert sum(line.amount_including_gst for line in lines if line) == 118
    assert sum(line.base_excluding_gst for line in lines if line) == 100


def test_unreconciled_item_prices_are_not_shown_as_including_gst() -> None:
    xml = _invoice_xml(
        [("Laptop", "<AMOUNT>100</AMOUNT><TAXABLEAMOUNT>100</TAXABLEAMOUNT>")],
        total="130",
        cgst="9",
        sgst="9",
    )
    archived = TallyProcessedInvoice(
        tally_voucher_guid="gst-test", raw_xml_gzip=gzip.compress(xml.encode())
    )
    totals, items = _present_invoice_amounts(archived, [])

    assert totals.grand_total == 130
    assert items[0].amount_excluding_gst == 100
    assert items[0].amount_including_gst is None


def test_older_invoice_can_reconcile_from_recorded_lines_without_xml() -> None:
    invoice = TallyProcessedInvoice(
        grand_total=Decimal("177"),
        cgst_amount=Decimal("13.50"),
        sgst_amount=Decimal("13.50"),
    )
    records = [
        TallyProcessedInvoiceLine(line_index=0, sale_id=1, line_total=Decimal("100")),
        TallyProcessedInvoiceLine(
            line_index=1, is_additional_product=True, line_total=Decimal("50")
        ),
    ]
    totals, items = _present_invoice_amounts(invoice, records)

    assert totals.grand_total == 177
    assert [item.amount_including_gst for item in items] == [118, 59]
