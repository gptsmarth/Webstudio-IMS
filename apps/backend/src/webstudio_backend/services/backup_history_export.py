"""Backup history export — Excel and PDF."""

from __future__ import annotations

import io
from datetime import UTC, datetime

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BACKUP_HISTORY_HEADERS = [
    "Backup Name",
    "Type",
    "Trigger",
    "Date",
    "Creator",
    "Duration (ms)",
    "Size (bytes)",
    "Checksum",
    "Status",
    "Verification",
    "Version",
    "Archived",
]


def backup_history_row_values(entry: dict) -> list[object]:
    return [
        entry.get("filename", ""),
        entry.get("backup_type", ""),
        entry.get("trigger_type", ""),
        entry.get("created_at", ""),
        entry.get("creator_display_name") or "",
        entry.get("duration_ms") or "",
        entry.get("size_bytes", 0),
        entry.get("checksum_sha256") or "",
        entry.get("status", ""),
        entry.get("verification_status", ""),
        entry.get("app_version") or "",
        "yes" if entry.get("is_archived") else "no",
    ]


def build_backup_history_xlsx(title: str, rows: list[dict]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Backup History"
    sheet.append([title])
    sheet.append(BACKUP_HISTORY_HEADERS)
    for entry in rows:
        sheet.append(backup_history_row_values(entry))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_backup_history_pdf(title: str, rows: list[dict]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    table_data = [BACKUP_HISTORY_HEADERS] + [backup_history_row_values(row) for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ],
        ),
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()


def backup_history_export_filename(export_format: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    extension = "xlsx" if export_format == "xlsx" else "pdf"
    return f"backup-history-{stamp}.{extension}"
