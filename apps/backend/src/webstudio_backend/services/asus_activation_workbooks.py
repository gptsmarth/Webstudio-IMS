"""Read ASUS source workbooks without evaluating formulas or opening external links."""

from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from webstudio_backend.core.exceptions import AppError
from webstudio_backend.integrations.tally.xml_parser import normalize_serial

MAX_FILE_BYTES = 10 * 1024 * 1024
_MAX_UNCOMPRESSED_BYTES = 60 * 1024 * 1024
_MAX_ROWS = 25_000
_MAX_COLUMNS = 150
CENT = Decimal("0.01")
_SCHEME_CODE = re.compile(r"\b([A-Z]{1,5}\d{5,})\b", re.IGNORECASE)
_CREDIT_HEADERS = {"cnunit", "cnperunit", "cntopartner", "cnamountperunit"}
_PRICE_HEADERS = {"supportedsrp", "suportedsrp", "novsuportedsrp", "eventsupportedsrp"}
_MODEL_HEADERS = ("modelname", "modelnumber", "model", "sku")


def invalid(message: str) -> AppError:
    return AppError("VALIDATION_ERROR", message, 422)


def model_key(raw: object) -> str:
    value = str(raw or "")
    value = unicodedata.normalize("NFKC", value).translate(str.maketrans("–—‑−", "----"))
    return re.sub(r"\s*-\s*", "-", value.strip()).upper()


def scheme_code(value: str) -> str | None:
    match = _SCHEME_CODE.search(value)
    return match[1].upper() if match else None


def money(value: object) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("Amount is missing.")
    text = str(value).strip().removeprefix("₹").replace(",", "").strip()
    try:
        amount = Decimal(text)
        if not amount.is_finite() or not 0 <= amount < 10**10:
            raise ValueError("Amount is outside the supported range.")
        rounded = amount.quantize(CENT, rounding=ROUND_HALF_UP)
        if rounded >= 10**10:
            raise ValueError("Amount is outside the supported range.")
        return rounded
    except InvalidOperation as exc:
        raise ValueError("Amount is not a valid number.") from exc


def _header(v: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(v or "").lower())


def _cell(row: tuple, index: int | None) -> object:
    return row[index] if index is not None and index < len(row) else None


def _text(row: tuple, index: int | None) -> str:
    return str(_cell(row, index) or "").strip()


@contextmanager
def _workbook(content: bytes) -> Iterator:
    if not content or len(content) > MAX_FILE_BYTES:
        raise invalid("Upload a non-empty Excel workbook of up to 10 MB.")
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            if (
                len(members) > 2000
                or sum(item.file_size for item in members) > _MAX_UNCOMPRESSED_BYTES
            ):
                raise invalid("The Excel workbook is too large when unpacked.")
            if any(item.flag_bits & 1 for item in members):
                raise invalid("Upload an Excel workbook without password protection.")
        workbook = load_workbook(
            io.BytesIO(content), read_only=True, data_only=True, keep_links=False
        )
    except (BadZipFile, InvalidFileException, OSError, ValueError, KeyError, ParseError) as exc:
        raise invalid("Open a valid .xlsx workbook and upload it again.") from exc
    try:
        yield workbook
    except (BadZipFile, OSError, ParseError) as exc:
        raise invalid("The workbook contains an unreadable worksheet.") from exc
    finally:
        workbook.close()


def _find_rows(sheet):
    if (sheet.max_row or 0) > _MAX_ROWS or (sheet.max_column or 0) > _MAX_COLUMNS:
        raise invalid(f"The worksheet {sheet.title} exceeds the supported row or column limit.")
    for line, row in enumerate(sheet.iter_rows(max_col=_MAX_COLUMNS, values_only=True), 1):
        if line > _MAX_ROWS:
            raise invalid(f"The worksheet {sheet.title} exceeds the supported row limit.")
        yield line, row


def _index(labels: list[str], names) -> int | None:
    return next((i for i, label in enumerate(labels) if label in names), None)


def parse_scheme(content: bytes) -> dict[str, dict]:
    rules: dict[str, dict] = {}
    with _workbook(content) as workbook:
        for sheet in workbook:
            if _header(sheet.title).startswith("gamingt3"):
                continue
            rows = _find_rows(sheet)
            for line, header in rows:
                if line > 20:
                    break
                labels = [_header(cell) for cell in header]
                model = next(
                    (labels.index(name) for name in _MODEL_HEADERS if name in labels), None
                )
                cn = _index(labels, _CREDIT_HEADERS)
                srp = next(
                    (
                        i
                        for i, label in enumerate(labels)
                        if label in _PRICE_HEADERS or label.endswith("supportedsrp")
                    ),
                    None,
                )
                if model is not None and cn is not None:
                    break
            else:
                continue
            if line > 20 or model is None or cn is None:
                continue
            part = _index(labels, {"partnumber", "partno"})
            claim = _index(labels, {"claimcode", "schemecode", "scheme"})
            period = _index(labels, {"programperiod", "programmeperiod", "period"})
            heading = next((str(cell) for cell in header if cell and scheme_code(str(cell))), "")
            if period is None and heading:
                period = header.index(heading)
            for line, row in rows:
                sku = model_key(_cell(row, model))
                raw_cn = _cell(row, cn)
                if not sku or raw_cn is None or str(raw_cn).strip() in ("", "-", "—", "N/A", "NA"):
                    continue
                try:
                    cn_value = money(raw_cn)
                    if not cn_value:
                        continue
                    raw_srp = _cell(row, srp)
                    srp_value = money(raw_srp) if raw_srp not in (None, "") else None
                except ValueError as exc:
                    raise invalid(f"{sheet.title}, row {line}: {exc}") from exc
                if len(sku) > 128:
                    raise invalid(f"{sheet.title}, row {line}: model number is too long.")
                source_period = _text(row, period)
                code = scheme_code(_text(row, claim) or heading or source_period)
                rule = {
                    "cn": str(cn_value),
                    "srp": str(srp_value) if srp_value else None,
                    "part_number": _text(row, part)[:128] or None,
                    "sheet": sheet.title,
                    "row": line,
                    "scheme_code": code,
                    "program_period": source_period[:500] or None,
                }
                existing = rules.get(sku)
                if existing:
                    if any(existing[k] != rule[k] for k in ("cn", "srp", "scheme_code")):
                        raise invalid(
                            f"Conflicting activation rates for {sku} in {existing['sheet']} and {sheet.title}."
                        )
                    continue
                rules[sku] = rule
    if not rules:
        raise invalid("No positive CN per unit rates were found in the workbook.")
    return rules


def _receipt_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y", "%Y%m%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError("Release Date is missing or invalid.")


def parse_receipts(content: bytes) -> list[dict]:
    receipts = []
    with _workbook(content) as workbook:
        for sheet in workbook:
            for line, header in (rows := _find_rows(sheet)):
                if line > 20:
                    break
                columns = {_header(value): i for i, value in enumerate(header)}
                if {"modelname", "imei", "cnamt", "releasedate"} <= columns.keys():
                    break
            else:
                continue
            if line > 20 or not {"modelname", "imei", "cnamt", "releasedate"} <= columns.keys():
                continue
            for line, row in rows:
                model = model_key(_cell(row, columns["modelname"]))
                raw_serial = _cell(row, columns["imei"])
                raw_amount = _cell(row, columns["cnamt"])
                if not model and raw_serial is None and raw_amount is None:
                    continue
                category = _text(row, columns.get("schemecategory"))
                if category and category.casefold() != "activation":
                    continue
                try:
                    if (
                        isinstance(raw_serial, float)
                        or isinstance(raw_serial, int)
                        and raw_serial >= 10**15
                    ):
                        raise ValueError("IMEI must be stored as text to preserve all digits.")
                    serial = normalize_serial(str(raw_serial or ""))
                    if not serial or not model or len(model) > 128 or len(serial) > 128:
                        raise ValueError("Valid IMEI and Model_Name are required.")
                    amount = money(raw_amount)
                    released = _receipt_date(_cell(row, columns["releasedate"]))
                except ValueError as exc:
                    raise invalid(f"{sheet.title}, row {line}: {exc}") from exc
                scheme = _text(row, columns.get("scheme"))[:500]
                application = _text(
                    row, columns.get("apllicationno", columns.get("applicationno"))
                )[:128]
                key = "\x1f".join((model, serial, scheme, application, str(released), str(amount)))
                receipts.append(
                    {
                        "sheet": sheet.title,
                        "row": line,
                        "model": model,
                        "serial": serial,
                        "amount": str(amount),
                        "release_date": str(released),
                        "scheme": scheme,
                        "application_no": application,
                        "digest": hashlib.sha256(key.encode()).hexdigest(),
                    }
                )
    if not receipts:
        raise invalid(
            "No activation receipts with Model_Name, IMEI, CN Amt and Release Date were found."
        )
    return receipts
