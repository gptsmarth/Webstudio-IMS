#!/usr/bin/env python3
"""Phase 1 — Analyze production Tally daybook XML (read-only, no DB writes)."""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag).upper() == name.upper():
            text = (child.text or "").strip()
            return text or None
    return None


def children_by_name(element: ET.Element, name: str) -> list[ET.Element]:
    target = name.upper()
    return [c for c in element if local_name(c.tag).upper() == target]


def parse_date(value: str | None) -> str:
    if not value:
        return ""
    cleaned = value.strip()
    if len(cleaned) == 8 and cleaned.isdigit():
        return datetime.strptime(cleaned, "%Y%m%d").strftime("%Y-%m-%d")
    return cleaned


def extract_serial(line: ET.Element) -> str | None:
    for batch in line.iter():
        if local_name(batch.tag).upper() == "SERIALNUMBER":
            text = (batch.text or "").strip()
            if text:
                return text
    for desc_list in children_by_name(line, "BASICUSERDESCRIPTION.LIST"):
        for item in children_by_name(desc_list, "BASICUSERDESCRIPTION"):
            text = (item.text or "").strip()
            if text and re.match(r"^[A-Z0-9]{8,}$", text, re.I):
                return text.upper()
    return None


def infer_brand(stock_item: str) -> str:
    upper = stock_item.upper()
    for brand in ("ASUS", "ACER", "LENOVO", "HP", "DELL", "MSI", "EPSON", "G & G"):
        if brand in upper:
            return brand.title().replace("G & G", "G&G")
    return "Unknown"


def is_laptop_line(stock_item: str) -> bool:
    upper = stock_item.upper()
    laptop_hints = (
        "VIVOBOOK", "ASPIRE", "IDEAPAD", "INSPIRON", "PAVILION", "THINKPAD",
        "NOTEBOOK", "LAPTOP", "E1504", "A325", "X1502", "L27-4C",
    )
    non_laptop = ("TONNER", "CARTRIDGE", "ADAPTER", "MOUSE", "BACKPACK", "CARRY CASE", "L3350")
    if any(n in upper for n in non_laptop):
        return False
    return any(h in upper for h in laptop_hints) or "UN." in upper or "BQ" in upper


@dataclass
class LineRow:
    voucher_index: int
    line_index: int
    company: str
    voucher_type: str
    printed_invoice: str
    internal_voucher: str
    invoice_date: str
    customer: str
    brand: str
    product_model: str
    serial_number: str | None
    quantity: str
    guid: str
    master_id: str | None
    is_laptop: bool


@dataclass
class AnalysisReport:
    company_name: str = ""
    rows: list[LineRow] = field(default_factory=list)
    voucher_count: int = 0
    voucher_types: Counter = field(default_factory=Counter)


def load_xml_root(xml_path: Path) -> ET.Element:
    raw = xml_path.read_text(encoding="utf-8", errors="replace")
    # Tally exports may contain invalid XML character references (e.g. &#4;).
    raw = re.sub(r"&#(\d+);", lambda m: "" if int(m.group(1)) < 32 else m.group(0), raw)
    # Strip raw control characters invalid in XML 1.0 (keep tab, LF, CR).
    cleaned: list[str] = []
    for ch in raw:
        code = ord(ch)
        if code in (0x9, 0xA, 0xD) or 0x20 <= code <= 0xD7FF or 0xE000 <= code <= 0xFFFD:
            cleaned.append(ch)
    return ET.fromstring("".join(cleaned))


def analyze(xml_path: Path) -> AnalysisReport:
    root = load_xml_root(xml_path)
    company = ""
    for elem in root.iter():
        if local_name(elem.tag).upper() == "SVCURRENTCOMPANY":
            company = (elem.text or "").strip()
            break

    report = AnalysisReport(company_name=company)
    voucher_index = 0

    for voucher in root.iter():
        if local_name(voucher.tag).upper() != "VOUCHER":
            continue

        guid = child_text(voucher, "GUID") or voucher.attrib.get("REMOTEID", "")
        master_id = (child_text(voucher, "MASTERID") or "").strip() or None
        voucher_type = child_text(voucher, "VOUCHERTYPENAME") or voucher.attrib.get("VCHTYPE", "")
        internal = child_text(voucher, "VOUCHERNUMBER") or ""
        printed = child_text(voucher, "REFERENCE") or internal
        invoice_date = parse_date(child_text(voucher, "DATE"))
        customer = child_text(voucher, "PARTYLEDGERNAME") or child_text(voucher, "PARTYNAME") or ""

        report.voucher_count += 1
        report.voucher_types[voucher_type] += 1
        voucher_index += 1

        line_index = 0
        for child in voucher:
            tag = local_name(child.tag).upper()
            if tag not in {"ALLINVENTORYENTRIES.LIST", "INVENTORYENTRIES.LIST"}:
                continue
            stock = child_text(child, "STOCKITEMNAME") or ""
            qty = child_text(child, "ACTUALQTY") or child_text(child, "BILLEDQTY") or "1"
            serial = extract_serial(child)
            report.rows.append(
                LineRow(
                    voucher_index=voucher_index,
                    line_index=line_index,
                    company=company,
                    voucher_type=voucher_type,
                    printed_invoice=printed,
                    internal_voucher=internal,
                    invoice_date=invoice_date,
                    customer=customer,
                    brand=infer_brand(stock),
                    product_model=stock,
                    serial_number=serial,
                    quantity=qty.strip(),
                    guid=guid,
                    master_id=master_id,
                    is_laptop=is_laptop_line(stock),
                ),
            )
            line_index += 1

    return report


def print_report(report: AnalysisReport) -> None:
    print("=" * 100)
    print("WEBSTUDIO IMS — PHASE 1 XML ANALYSIS REPORT")
    print("=" * 100)
    print(f"\nCompany Name: {report.company_name}")
    print(f"Total Vouchers: {report.voucher_count}")
    print(f"Voucher Types: {dict(report.voucher_types)}")
    print()

    headers = [
        "#", "V.Type", "Printed Inv.", "Int. Voucher", "Date", "Customer",
        "Brand", "Product Model", "Serial", "Qty", "GUID", "MASTERID", "Laptop?",
    ]
    print(" | ".join(headers))
    print("-" * 180)

    for i, row in enumerate(report.rows, 1):
        print(
            " | ".join([
                str(i),
                row.voucher_type,
                row.printed_invoice,
                row.internal_voucher,
                row.invoice_date,
                (row.customer or "")[:20],
                row.brand,
                (row.product_model or "")[:35],
                row.serial_number or "—",
                row.quantity,
                (row.guid or "")[:20] + "…",
                row.master_id or "—",
                "Yes" if row.is_laptop else "No",
            ]),
        )

    serials = [r.serial_number for r in report.rows if r.serial_number]
    serial_dupes = [s for s, c in Counter(serials).items() if c > 1]
    models = [r.product_model for r in report.rows if r.is_laptop]
    model_dupes = [m for m, c in Counter(models).items() if c > 1]
    missing_serial_laptops = [r for r in report.rows if r.is_laptop and not r.serial_number]
    missing_model = [r for r in report.rows if not r.product_model.strip()]

    print("\n" + "=" * 100)
    print("DETECTION SUMMARY")
    print("=" * 100)
    print(f"Laptop lines: {sum(1 for r in report.rows if r.is_laptop)}")
    print(f"Non-laptop lines: {sum(1 for r in report.rows if not r.is_laptop)}")
    print(f"Lines with serial: {len(serials)}")
    print(f"Missing serial (laptop lines): {len(missing_serial_laptops)}")
    print(f"Duplicate serials: {serial_dupes or 'None'}")
    print(f"Duplicate laptop models (expected): {len(model_dupes)} unique models reused")
    print(f"Missing product model: {len(missing_model)}")

    if missing_serial_laptops:
        print("\nMissing serial (laptop lines):")
        for r in missing_serial_laptops:
            print(f"  - Voucher {r.internal_voucher} / {r.product_model}")

    laptop_rows = [r for r in report.rows if r.is_laptop]
    print("\nUnique laptop product models:")
    for model in sorted({r.product_model for r in laptop_rows}):
        count = sum(1 for r in laptop_rows if r.product_model == model)
        print(f"  - {model} ({count} line(s))")


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("daybook_response.xml")
    print_report(analyze(path))
