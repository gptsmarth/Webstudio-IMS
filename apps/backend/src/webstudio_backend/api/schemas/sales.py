"""Sales workspace API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from webstudio_backend.api.schemas.inventory import InventoryItemDetail
from webstudio_backend.infrastructure.repositories.report_repository import (
    SaleDetailRow,
    SalesReportRow,
)


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
            purchase_price=row.purchase_price if include_purchase_price else None,
            sale_source=row.sale_source,
            sold_at=row.sold_at,
            recorded_by_user_id=row.recorded_by_user_id,
            recorded_by_display_name=row.recorded_by_display_name,
        )


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
    purchase_price: float | None = None
    sale_source: str
    sold_at: datetime
    recorded_by_user_id: int | None
    recorded_by_display_name: str | None
    notes: str | None
    tally_company_name: str | None
    tally_voucher_number: str | None
    printed_invoice_number: str | None
    tally_voucher_type: str | None
    created_at: datetime

    @classmethod
    def from_row(
        cls, row: SaleDetailRow, *, include_purchase_price: bool = True
    ) -> SaleDetailResponse:
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
            purchase_price=row.purchase_price if include_purchase_price else None,
            sale_source=row.sale_source,
            sold_at=row.sold_at,
            recorded_by_user_id=row.recorded_by_user_id,
            recorded_by_display_name=row.recorded_by_display_name,
            notes=row.notes,
            tally_company_name=row.tally_company_name,
            tally_voucher_number=row.tally_voucher_number,
            printed_invoice_number=row.printed_invoice_number,
            tally_voucher_type=row.tally_voucher_type,
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
