"""Sales workspace API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from webstudio_backend.api.schemas.inventory import InventoryItemDetail
from webstudio_backend.infrastructure.repositories.report_repository import (
    SaleDetailRow,
    SalesReportRow,
)
from webstudio_backend.integrations.tally.xml_parser import format_serial_source_label


class SaleListItem(BaseModel):
    id: int
    inventory_item_id: uuid.UUID | None
    serial_number: str
    brand_name: str
    model_number: str
    model_name: str
    location_name: str
    invoice_number: str
    customer_name: str | None
    payment_mode: str | None
    sale_amount: float | None = None
    sale_amount_excluding_gst: float | None = None
    sale_cgst_amount: float | None = None
    sale_sgst_amount: float | None = None
    sale_igst_amount: float | None = None
    sale_cess_amount: float | None = None
    purchase_price: float | None = None
    sale_source: str
    sold_at: datetime
    recorded_by_user_id: int | None
    recorded_by_display_name: str | None

    @classmethod
    def from_row(cls, row: SalesReportRow, *, include_purchase_price: bool = True) -> SaleListItem:
        return cls(
            id=row.id,
            inventory_item_id=row.inventory_item_id,
            serial_number=row.serial_number,
            brand_name=row.brand_name,
            model_number=row.model_number,
            model_name=row.model_name,
            location_name=row.location_name,
            invoice_number=row.invoice_number,
            customer_name=row.customer_name,
            payment_mode=row.payment_mode,
            sale_amount=row.sale_amount,
            sale_amount_excluding_gst=row.sale_amount_excluding_gst,
            sale_cgst_amount=row.sale_cgst_amount,
            sale_sgst_amount=row.sale_sgst_amount,
            sale_igst_amount=row.sale_igst_amount,
            sale_cess_amount=row.sale_cess_amount,
            purchase_price=row.purchase_price if include_purchase_price else None,
            sale_source=row.sale_source,
            sold_at=row.sold_at,
            recorded_by_user_id=row.recorded_by_user_id,
            recorded_by_display_name=row.recorded_by_display_name,
        )


class AdditionalInvoiceProduct(BaseModel):
    """Case C1 — no serial (bag, warranty, software, consumables)."""

    line_index: int
    stock_item_name: str | None = None
    quantity: str | None = None
    rate: Decimal | None = None
    taxable_amount: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    cess_amount: Decimal | None = None
    line_total: Decimal | None = None
    extracted_serial: str | None = None
    match_result: str | None = None
    decision_reason: str | None = None


class UnmatchedSerializedItem(BaseModel):
    """Case C2 — serial extracted but not managed in IMS."""

    line_index: int
    product_name: str | None = None
    serial_number: str | None = None
    serial_source: str | None = None
    serial_source_label: str | None = None
    invoice_amount: Decimal | None = None
    reason: str = "Serial not managed in IMS"


class TrackedInvoiceProduct(BaseModel):
    """Inventory-tracked line that produced a sale (Case A/B)."""

    line_index: int
    product_name: str | None = None
    serial_number: str | None = None
    serial_source: str | None = None
    serial_source_label: str | None = None
    sale_id: int | None = None
    rate: Decimal | None = None
    line_total: Decimal | None = None
    review_required: bool = False


class InvoiceTotals(BaseModel):
    subtotal: Decimal | None = None
    discount_amount: Decimal | None = None
    round_off: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    cess_amount: Decimal | None = None
    grand_total: Decimal | None = None


class SaleDetailResponse(BaseModel):
    id: int
    inventory_item_id: uuid.UUID | None
    serial_number: str
    brand_id: int | None
    brand_name: str
    product_model_id: uuid.UUID | None
    model_number: str
    model_name: str
    location_id: int | None
    location_name: str
    color: str
    cpu: str
    ram_gb: int | None
    storage_value: str
    storage_unit: str
    storage_type: str
    invoice_number: str
    customer_name: str | None
    payment_mode: str | None
    sale_amount: float | None = None
    sale_amount_excluding_gst: float | None = None
    sale_cgst_amount: float | None = None
    sale_sgst_amount: float | None = None
    sale_igst_amount: float | None = None
    sale_cess_amount: float | None = None
    purchase_price: float | None = None
    sale_source: str
    sold_at: datetime
    recorded_by_user_id: int | None
    recorded_by_display_name: str | None
    notes: str | None
    tally_company_name: str | None
    tally_voucher_number: str | None
    printed_invoice_number: str | None
    tally_voucher_guid: str | None = None
    tally_master_id: str | None = None
    tally_voucher_type: str | None
    review_required: bool = False
    review_reason: str | None = None
    invoice_model_name: str | None = None
    ims_model_name: str | None = None
    serial_source: str | None = None
    serial_source_label: str | None = None
    invoice_status: str | None = None
    tracked_products: list[TrackedInvoiceProduct] = Field(default_factory=list)
    additional_products: list[AdditionalInvoiceProduct] = Field(default_factory=list)
    unmatched_serialized_items: list[UnmatchedSerializedItem] = Field(default_factory=list)
    invoice_totals: InvoiceTotals | None = None
    original_xml_available: bool = False
    imported_at: datetime | None = None
    created_at: datetime

    @classmethod
    def from_row(
        cls,
        row: SaleDetailRow,
        *,
        include_purchase_price: bool = True,
        include_serial_source: bool = False,
        tracked_products: list[TrackedInvoiceProduct] | None = None,
        additional_products: list[AdditionalInvoiceProduct] | None = None,
        unmatched_serialized_items: list[UnmatchedSerializedItem] | None = None,
        invoice_totals: InvoiceTotals | None = None,
        invoice_status: str | None = None,
        original_xml_available: bool = False,
        imported_at: datetime | None = None,
    ) -> SaleDetailResponse:
        serial_source = row.serial_source if include_serial_source else None
        return cls(
            id=row.id,
            inventory_item_id=row.inventory_item_id,
            serial_number=row.serial_number,
            brand_id=row.brand_id,
            brand_name=row.brand_name,
            product_model_id=row.product_model_id,
            model_number=row.model_number,
            model_name=row.model_name,
            location_id=row.location_id,
            location_name=row.location_name,
            color=row.color,
            cpu=row.cpu,
            ram_gb=row.ram_gb,
            storage_value=row.storage_value,
            storage_unit=row.storage_unit,
            storage_type=row.storage_type,
            invoice_number=row.invoice_number,
            customer_name=row.customer_name,
            payment_mode=row.payment_mode,
            sale_amount=row.sale_amount,
            sale_amount_excluding_gst=row.sale_amount_excluding_gst,
            sale_cgst_amount=row.sale_cgst_amount,
            sale_sgst_amount=row.sale_sgst_amount,
            sale_igst_amount=row.sale_igst_amount,
            sale_cess_amount=row.sale_cess_amount,
            purchase_price=row.purchase_price if include_purchase_price else None,
            sale_source=row.sale_source,
            sold_at=row.sold_at,
            recorded_by_user_id=row.recorded_by_user_id,
            recorded_by_display_name=row.recorded_by_display_name,
            notes=row.notes,
            tally_company_name=row.tally_company_name,
            tally_voucher_number=row.tally_voucher_number,
            printed_invoice_number=row.printed_invoice_number,
            tally_voucher_guid=row.tally_voucher_guid,
            tally_master_id=row.tally_master_id,
            tally_voucher_type=row.tally_voucher_type,
            review_required=row.review_required,
            review_reason=row.review_reason,
            invoice_model_name=row.invoice_model_name,
            ims_model_name=row.ims_model_name,
            serial_source=serial_source,
            serial_source_label=(
                format_serial_source_label(serial_source) if include_serial_source else None
            ),
            invoice_status=invoice_status,
            tracked_products=tracked_products or [],
            additional_products=additional_products or [],
            unmatched_serialized_items=unmatched_serialized_items or [],
            invoice_totals=invoice_totals,
            original_xml_available=original_xml_available,
            imported_at=imported_at,
            created_at=row.created_at,
        )


class CancelSaleRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class CancelledSaleSummary(BaseModel):
    id: int
    invoice_number: str
    serial_number: str
    cancelled_at: datetime
    cancellation_reason: str | None


class CancelSaleResponse(BaseModel):
    inventory: InventoryItemDetail
    sale: CancelledSaleSummary
