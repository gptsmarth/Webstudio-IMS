"""ASUS activation schemes, claims and receipt reconciliation."""

from __future__ import annotations

import asyncio
import hashlib
import io
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import ReportsExportDep, SettingsModifyDep
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.services.asus_activation import AsusActivationService, workbook_file_name
from webstudio_backend.services.asus_activation_workbooks import (
    MAX_FILE_BYTES,
    invalid,
    parse_receipts,
    parse_scheme,
)
from webstudio_backend.services.asus_weekly_report_service import ASUS_WORKBOOK_MEDIA_TYPE

router = APIRouter(prefix="/api/v1/asus-activation", tags=["asus-activation"])
Session = Annotated[AsyncSession, DbSessionDep]
MonthFilter = Annotated[str | None, Query(pattern=r"^[0-9]{4}-[0-9]{2}$")]
WorkbookUpload = Annotated[UploadFile, File()]
StatusFilter = Literal["pending", "discrepancy", "received", "all"]
Search = Annotated[str, Query(max_length=160)]
SchemeMode = Literal["dates", "replace", "supplement"]

_COLUMNS = (
    ("sold_on", "Invoice Date"),
    ("invoice", "Invoice No"),
    ("customer", "Customer"),
    ("model", "Model"),
    ("serial", "Serial / IMEI"),
    ("unit_price", "Unit Price Incl GST"),
    ("nov_t2_dbp", "NOV T2 DBP"),
    ("supported_srp", "Supported SRP"),
    ("supported_dbp", "Supported DBP"),
    ("support_on_srp", "Support on SRP"),
    ("expected_amount", "CN/Unit (expected)"),
    ("date_from", "Activation From"),
    ("date_to", "Activation To"),
    ("scheme_code", "Activation Code"),
    ("source_sheet", "Rate Worksheet"),
    ("program_period", "Workbook Programme Dates"),
    ("scheme_filename", "Activation Workbook"),
    ("scheme_expected", "Scheme CN/Unit"),
    ("expected_note", "Expected CN Correction Note"),
    ("original_expected", "Expected CN When Received"),
    ("received_amount", "Received CN Excl GST"),
    ("variance", "Variance"),
    ("status", "Status"),
    ("cancelled", "Sale Cancelled"),
    ("scheme_applies", "Current Scheme Applies"),
    ("receipt_source", "Receipt Source"),
    ("receipt_filename", "Receipt Workbook"),
    ("receipt_scheme", "Receipt Scheme"),
    ("application_no", "Application No"),
    ("release_date", "Release Date"),
    ("recorded_at", "Receipt Recorded At"),
    ("record_note", "Receipt Note"),
    ("resolution_note", "Resolution Note"),
    ("resolved_at", "Resolved At"),
)
_MONEY_COLUMNS = {
    "unit_price",
    "nov_t2_dbp",
    "supported_srp",
    "supported_dbp",
    "support_on_srp",
    "expected_amount",
    "scheme_expected",
    "original_expected",
    "received_amount",
    "variance",
}
_DATE_COLUMNS = {"sold_on", "date_from", "date_to", "release_date"}


class ManualReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Literal["record", "resolve"]
    amount: str | None = Field(default=None, max_length=32)
    note: str = Field(default="", max_length=2000)


class ExpectedCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    amount: str | None = Field(max_length=32)
    note: str = Field(min_length=1, max_length=2000)
    scope: Literal["sale", "model"] = "sale"


class RateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    use: Literal["existing", "incoming"]
    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def valid_dates(self):
        if (self.date_from is None) != (self.date_to is None) or (
            self.use == "existing" and self.date_from is not None
        ):
            raise ValueError("Select both dates for a custom incoming rate.")
        return self


_RATE_DECISIONS = TypeAdapter(dict[str, RateDecision])


async def _read_file(file: UploadFile) -> bytes:
    try:
        content = await file.read(MAX_FILE_BYTES + 1)
    finally:
        await file.close()
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise invalid("Select an .xlsx workbook.")
    if not content or len(content) > MAX_FILE_BYTES:
        raise invalid("Upload a non-empty Excel workbook of up to 10 MB.")
    return content


@router.get("")
async def activation_dashboard(
    request: Request,
    reader: ReportsExportDep,
    session: Session,
    month: MonthFilter = None,
    search: Search = "",
) -> dict:
    return build_envelope(
        request, await AsusActivationService(session).dashboard(month, search.strip())
    )


@router.post("/schemes")
async def upload_scheme(
    request: Request,
    reader: ReportsExportDep,
    editor: SettingsModifyDep,
    session: Session,
    file: WorkbookUpload,
    date_from: Annotated[date, Form()],
    date_to: Annotated[date, Form()],
) -> dict:
    content = await _read_file(file)
    rules = await asyncio.to_thread(parse_scheme, content)
    scheme = await AsusActivationService(session).upload_scheme(
        date_from,
        date_to,
        file.filename,
        content,
        rules,
        editor.user.id,
    )
    await session.commit()
    return build_envelope(request, scheme)


@router.post("/schemes/{scheme_id}/edit")
async def edit_scheme(
    request: Request,
    reader: ReportsExportDep,
    editor: SettingsModifyDep,
    session: Session,
    scheme_id: UUID,
    mode: Annotated[SchemeMode, Form()],
    date_from: Annotated[date, Form()],
    date_to: Annotated[date, Form()],
    file: Annotated[UploadFile | None, File()] = None,
    preview_id: Annotated[str | None, Form(pattern=r"^[a-f0-9]{64}$")] = None,
    choices: Annotated[str, Form(max_length=4_000_000)] = "{}",
) -> dict:
    if (mode == "dates") != (file is None):
        raise invalid("Select a workbook for replace or add. Use Edit dates for date changes only.")
    try:
        decisions = _RATE_DECISIONS.validate_json(choices)
    except ValidationError as exc:
        raise invalid("Choose a valid rate and date range for each conflicting model.") from exc
    content = await _read_file(file) if file else None
    result = await AsusActivationService(session).edit_scheme(
        scheme_id,
        date_from,
        date_to,
        mode,
        workbook_file_name(file.filename) if file else None,
        hashlib.sha256(content).hexdigest() if content else None,
        await asyncio.to_thread(parse_scheme, content) if content else None,
        editor.user.id,
        preview_id,
        {sku: decision.model_dump(mode="json") for sku, decision in decisions.items()},
    )
    if preview_id is not None:
        await session.commit()
    return build_envelope(request, result)


@router.post("/receipts")
async def import_receipts(
    request: Request,
    reader: ReportsExportDep,
    editor: SettingsModifyDep,
    session: Session,
    file: WorkbookUpload,
    preview_id: Annotated[str | None, Form(pattern=r"^[a-f0-9]{64}$")] = None,
) -> dict:
    content = await _read_file(file)
    rows = await asyncio.to_thread(parse_receipts, content)
    result = await AsusActivationService(session).reconcile(
        rows, content, file.filename, editor.user.id, preview_id
    )
    if preview_id is not None:
        await session.commit()
    return build_envelope(request, result)


@router.post("/claims/{sale_id}/receipt")
async def update_claim(
    request: Request,
    reader: ReportsExportDep,
    editor: SettingsModifyDep,
    session: Session,
    sale_id: int,
    body: ManualReceipt,
) -> dict:
    claim = await AsusActivationService(session).record_manual(
        sale_id, body.action, body.amount, body.note, editor.user.id
    )
    await session.commit()
    return build_envelope(request, claim)


@router.put("/claims/{sale_id}/expected")
async def correct_expected(
    request: Request,
    reader: ReportsExportDep,
    editor: SettingsModifyDep,
    session: Session,
    sale_id: int,
    body: ExpectedCorrection,
) -> dict:
    claim = await AsusActivationService(session).correct_expected(
        sale_id, body.amount, body.note, body.scope, editor.user.id
    )
    await session.commit()
    return build_envelope(request, claim)


def _write_excel(claims: list[dict]) -> bytes:
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("ASUS Activation")
    sheet.freeze_panes = "D2"
    sheet.auto_filter.ref = f"A1:{get_column_letter(len(_COLUMNS))}{len(claims) + 1}"
    header = []
    for index, (key, name) in enumerate(_COLUMNS, 1):
        sheet.column_dimensions[get_column_letter(index)].width = max(16, min(32, len(name) + 4))
        cell = WriteOnlyCell(sheet, name)
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="1F6655" if key == "expected_amount" else "18334B")
        header.append(cell)
    sheet.append(header)
    for claim in claims:
        cells = []
        for key, _ in _COLUMNS:
            value = claim[key]
            cell = WriteOnlyCell(sheet)
            if value is not None and key in _MONEY_COLUMNS:
                cell.value = float(value)
                cell.number_format = "#,##0.00"
            elif value is not None and key in _DATE_COLUMNS:
                cell.value = date.fromisoformat(value)
                cell.number_format = "dd/mm/yyyy"
            elif isinstance(value, str):
                cell.value = ILLEGAL_CHARACTERS_RE.sub("", value)
                cell.data_type = "s"
            else:
                cell.value = value
            if key == "expected_amount":
                cell.font = Font(bold=True, color="17483C")
                cell.fill = PatternFill("solid", fgColor="E2F3EC")
            cells.append(cell)
        sheet.append(cells)
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


@router.get("/export")
async def export_claims(
    reader: ReportsExportDep,
    session: Session,
    month: MonthFilter = None,
    status: StatusFilter = "all",
    search: Search = "",
) -> Response:
    search = search.strip()
    claims = await AsusActivationService(session).claims(None if search else month, search=search)
    if status != "all":
        claims = [claim for claim in claims if claim["status"] == status]
    content = await asyncio.to_thread(_write_excel, claims)
    filename = f"ASUS-Activation-{('search' if search else month or 'all-months')}-{status}.xlsx"
    return Response(
        content=content,
        media_type=ASUS_WORKBOOK_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )
