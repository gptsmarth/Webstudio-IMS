"""Sales workspace API endpoints."""

from __future__ import annotations

import gzip
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    MainAdminDep,
    SalesCancelDep,
    SalesViewDep,
)
from webstudio_backend.api.response_helpers import build_page_meta
from webstudio_backend.api.sales_errors import raise_sale_error
from webstudio_backend.api.schemas.inventory import InventoryItemDetail
from webstudio_backend.api.schemas.responses import Envelope, ResponseMeta, utc_now_iso
from webstudio_backend.api.schemas.sales import (
    AdditionalInvoiceProduct,
    CancelledSaleSummary,
    CancelSaleRequest,
    CancelSaleResponse,
    InvoiceTotals,
    SaleDetailResponse,
    SaleInvoiceItem,
    SaleListItem,
    TrackedInvoiceProduct,
    UnmatchedSerializedItem,
)
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    SaleSource,
    UserRole,
    tally_invoice_status_label,
)
from webstudio_backend.infrastructure.database.models.tally_processed_invoice import (
    TallyProcessedInvoice,
)
from webstudio_backend.infrastructure.database.models.tally_processed_invoice_line import (
    TallyProcessedInvoiceLine,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.report_filters import ReportFilters
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_line_repository import (
    TallyProcessedInvoiceLineRepository,
)
from webstudio_backend.infrastructure.repositories.tally_processed_invoice_repository import (
    TallyProcessedInvoiceRepository,
)
from webstudio_backend.integrations.tally.gst import (
    GST_FIELDS,
    line_gst_breakdown,
    reconcile_invoice_lines,
)
from webstudio_backend.integrations.tally.types import TallyInventoryLine, TallyVoucherTotals
from webstudio_backend.integrations.tally.xml_parser import (
    format_serial_source_label,
    read_archived_voucher,
)
from webstudio_backend.services.report_service import ReportService
from webstudio_backend.services.sale_service import SaleService

router = APIRouter(prefix="/api/v1/sales", tags=["sales"])


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return Envelope(
        data=data,
        meta=meta,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _page_meta(page: int, page_size: int, total_items: int, total_pages: int) -> ResponseMeta:
    return build_page_meta(page, page_size, total_items, total_pages)


def _can_view_purchase_price(current: AuthenticatedUser) -> bool:
    return current.user.role in {UserRole.MAIN_ADMIN, UserRole.ADMIN}


def _can_view_serial_source_audit(current: AuthenticatedUser) -> bool:
    return current.user.role is UserRole.MAIN_ADMIN


def _actor(current: AuthenticatedUser) -> AuditActor:
    return AuditActor(
        user_id=current.user.id,
        display_name=current.user.display_name,
        role=current.user.role.value,
    )


def _sale_list_payload(row, *, current: AuthenticatedUser) -> dict:
    include_purchase = _can_view_purchase_price(current)
    response = SaleListItem.from_row(row, include_purchase_price=include_purchase)
    exclude = set() if include_purchase else {"purchase_price"}
    return response.model_dump(exclude=exclude)


def _invoice_item(
    line: TallyInventoryLine, linked: list[TallyProcessedInvoiceLine], *, totals: InvoiceTotals
) -> SaleInvoiceItem:
    if any(record.sale_id is not None for record in linked):
        tracking = "tracked"
    elif any(record.is_additional_product for record in linked):
        tracking = "additional"
    elif any(record.is_unmatched_serialized for record in linked):
        tracking = "unmatched"
    else:
        tracking = "unclassified"
    breakdown = line_gst_breakdown(line)
    voucher_has_gst = any(getattr(totals, field) for field in GST_FIELDS)
    untaxed_amount = (
        Decimal(line.line_total) if line.line_total is not None and not voucher_has_gst else None
    )
    inclusive_amount = untaxed_amount
    if breakdown is not None and all(
        getattr(line, field) is not None for field in GST_FIELDS if getattr(totals, field)
    ):
        inclusive_amount = breakdown.amount_including_gst
    return SaleInvoiceItem(
        line_index=line.line_index,
        product_name=line.stock_item_name,
        quantity=line.quantity,
        tracking=tracking,
        amount_excluding_gst=(
            breakdown.base_excluding_gst
            if breakdown is not None
            else untaxed_amount if totals.subtotal is not None else None
        ),
        amount_including_gst=inclusive_amount,
        gst_allocated=line.gst_allocated,
        **{
            field: Decimal(value) if (value := getattr(line, field)) is not None else None
            for field in GST_FIELDS
        },
    )


def _present_invoice_amounts(
    invoice: TallyProcessedInvoice, records: list[TallyProcessedInvoiceLine]
) -> tuple[InvoiceTotals, list[SaleInvoiceItem]]:
    totals = InvoiceTotals.model_validate(invoice, from_attributes=True)
    parsed = read_archived_voucher(invoice.raw_xml_gzip, invoice.tally_voucher_guid)
    items: list[SaleInvoiceItem] = []
    if parsed is not None and parsed.inventory_lines:
        totals = InvoiceTotals.model_validate(parsed.totals, from_attributes=True)
        stored = {record.line_index: record for record in records}
        index = 0
        for line in parsed.inventory_lines:
            count = max(1, len(line.batch_allocations))
            matched = [stored[pos] for pos in range(index, index + count) if pos in stored]
            index += count
            items.append(_invoice_item(line, matched, totals=totals))
    else:
        lines = [
            TallyInventoryLine(
                line_index=record.line_index,
                stock_item_name=record.stock_item_name or "",
                quantity=record.quantity or "",
                serial_number=record.serial_number,
                taxable_amount=(
                    str(record.taxable_amount) if record.taxable_amount is not None else None
                ),
                line_total=str(record.line_total) if record.line_total is not None else None,
                amount=str(record.line_total) if record.line_total is not None else None,
                **{
                    field: str(value) if (value := getattr(record, field)) is not None else None
                    for field in GST_FIELDS
                },
            )
            for record in records
        ]
        if totals.grand_total is not None:
            lines, reconciled = reconcile_invoice_lines(
                lines, TallyVoucherTotals(**totals.model_dump())
            )
            totals = InvoiceTotals.model_validate(reconciled, from_attributes=True)
        for line, record in zip(lines, records, strict=True):
            items.append(_invoice_item(line, [record], totals=totals))
    return totals, items


async def _sale_detail_payload(
    row,
    *,
    current: AuthenticatedUser,
    db_session: AsyncSession,
) -> dict:
    include_purchase = _can_view_purchase_price(current)
    include_serial_source = _can_view_serial_source_audit(current)
    additional_products: list[AdditionalInvoiceProduct] = []
    unmatched_serialized_items: list[UnmatchedSerializedItem] = []
    tracked_products: list[TrackedInvoiceProduct] = []
    invoice_totals: InvoiceTotals | None = None
    invoice_items: list[SaleInvoiceItem] = []
    invoice_status: str | None = None
    original_xml_available = False
    imported_at = None

    if row.tally_voucher_guid:
        line_repo = TallyProcessedInvoiceLineRepository(db_session)
        invoice = await TallyProcessedInvoiceRepository(db_session).find_latest_by_guid(
            row.tally_voucher_guid
        )
        if invoice is not None:
            original_xml_available = invoice.raw_xml_gzip is not None
            imported_at = invoice.imported_at
            invoice_status = tally_invoice_status_label(invoice.processing_status)
            records = await line_repo.list_for_invoice(invoice.id)
            invoice_totals, invoice_items = _present_invoice_amounts(invoice, records)
            additional_products = [
                AdditionalInvoiceProduct(
                    line_index=line.line_index,
                    stock_item_name=line.stock_item_name,
                    quantity=line.quantity,
                    rate=line.rate,
                    taxable_amount=line.taxable_amount,
                    cgst_amount=line.cgst_amount,
                    sgst_amount=line.sgst_amount,
                    igst_amount=line.igst_amount,
                    cess_amount=line.cess_amount,
                    line_total=line.line_total,
                    extracted_serial=line.serial_number,
                    match_result=line.match_result,
                    decision_reason=line.decision_reason,
                )
                for line in await line_repo.list_additional_products_for_guid(
                    row.tally_voucher_guid
                )
            ]
            unmatched_serialized_items = [
                UnmatchedSerializedItem(
                    line_index=line.line_index,
                    product_name=line.stock_item_name,
                    serial_number=line.serial_number,
                    serial_source=line.serial_source if include_serial_source else None,
                    serial_source_label=(
                        format_serial_source_label(line.serial_source)
                        if include_serial_source
                        else None
                    ),
                    invoice_amount=line.line_total,
                    reason=line.decision_reason or "Serial not managed in IMS",
                )
                for line in await line_repo.list_unmatched_serialized_for_guid(
                    row.tally_voucher_guid
                )
            ]
            tracked_products = [
                TrackedInvoiceProduct(
                    line_index=line.line_index,
                    product_name=line.stock_item_name,
                    serial_number=line.serial_number,
                    serial_source=line.serial_source if include_serial_source else None,
                    serial_source_label=(
                        format_serial_source_label(line.serial_source)
                        if include_serial_source
                        else None
                    ),
                    sale_id=line.sale_id,
                    rate=line.rate,
                    line_total=line.line_total,
                    review_required=bool(line.review_required),
                )
                for line in await line_repo.list_tracked_sale_lines_for_guid(row.tally_voucher_guid)
            ]

    response = SaleDetailResponse.from_row(
        row,
        include_purchase_price=include_purchase,
        include_serial_source=include_serial_source,
        tracked_products=tracked_products,
        additional_products=additional_products,
        unmatched_serialized_items=unmatched_serialized_items,
        invoice_totals=invoice_totals,
        invoice_items=invoice_items,
        invoice_status=invoice_status,
        original_xml_available=original_xml_available,
        imported_at=imported_at,
    )
    exclude = set() if include_purchase else {"purchase_price"}
    if not include_serial_source:
        exclude |= {"serial_source", "serial_source_label"}
    payload = response.model_dump(exclude=exclude)
    payload["invoice_items"] = [item.model_dump(mode="json") for item in invoice_items]
    return payload


def _parse_legacy_sort(sort: str | None) -> tuple[str | None, str | None]:
    if not sort:
        return None, None
    if ":" in sort:
        field, direction = sort.split(":", 1)
        return field.strip() or None, direction.strip() or None
    return sort.strip() or None, None


@router.get("")
async def list_sales(
    request: Request,
    current: SalesViewDep,
    db_session: AsyncSession = DbSessionDep,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    brand_id: int | None = None,
    location_id: int | None = None,
    product_model_id: uuid.UUID | None = None,
    user_id: int | None = None,
    invoice_number: str | None = None,
    customer_name: str | None = None,
    payment_mode: str | None = None,
    sale_source: SaleSource | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort: str | None = Query(default="sold_at:desc"),
    sort_field: str | None = None,
    sort_direction: str | None = None,
) -> dict:
    legacy_field, legacy_direction = _parse_legacy_sort(sort)
    filters = ReportFilters(
        date_from=date_from,
        date_to=date_to,
        brand_id=brand_id,
        location_id=location_id,
        product_model_id=product_model_id,
        user_id=user_id,
        invoice_number=invoice_number,
        customer_name=customer_name,
        payment_mode=payment_mode,
        sale_source=sale_source,
        search=search,
        sort_field=sort_field or legacy_field,
        sort_direction=sort_direction or legacy_direction,
    )
    result = await ReportService(db_session).sales_report(
        filters, PageParams(page=page, page_size=page_size)
    )
    return _envelope(
        request,
        [_sale_list_payload(row, current=current) for row in result.items],
        _page_meta(result.page, result.page_size, result.total_items, result.total_pages),
    )


@router.get("/{sale_id}")
async def get_sale(
    request: Request,
    sale_id: int,
    current: SalesViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    row = await ReportService(db_session).get_sale_detail(sale_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale not found.")
    return _envelope(
        request,
        await _sale_detail_payload(row, current=current, db_session=db_session),
    )


@router.get("/{sale_id}/original-xml")
async def get_sale_original_xml(
    sale_id: int,
    current: MainAdminDep,
    db_session: AsyncSession = DbSessionDep,
) -> Response:
    """Return archived Tally voucher XML for administrators."""
    row = await ReportService(db_session).get_sale_detail(sale_id)
    if row is None or not row.tally_voucher_guid:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale XML not found.")
    invoice = await TallyProcessedInvoiceRepository(db_session).find_latest_by_guid(
        row.tally_voucher_guid
    )
    if invoice is None or invoice.raw_xml_gzip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sale XML not found.")
    xml_bytes = gzip.decompress(invoice.raw_xml_gzip)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="tally-voucher-{row.tally_voucher_guid}.xml"'
            ),
        },
    )


@router.post("/{sale_id}/cancel")
async def cancel_sale(
    request: Request,
    sale_id: int,
    body: CancelSaleRequest,
    current: SalesCancelDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    try:
        result = await SaleService(db_session).cancel_sale(
            sale_id,
            reason=body.reason,
            actor=_actor(current),
        )
    except Exception as exc:
        raise_sale_error(exc)

    include_purchase = _can_view_purchase_price(current)
    response = CancelSaleResponse(
        inventory=InventoryItemDetail.from_row(
            result.inventory,
            include_purchase_price=include_purchase,
        ),
        sale=CancelledSaleSummary(
            id=result.sale.id,
            invoice_number=result.sale.invoice_number,
            serial_number=result.restored_serial_number,
            cancelled_at=result.sale.cancelled_at,
            cancellation_reason=result.sale.cancellation_reason,
        ),
    )
    payload = response.model_dump()
    if not include_purchase:
        payload["inventory"].pop("purchase_price", None)
    return _envelope(request, payload)
