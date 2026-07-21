"""Purchase Import Queue API schemas (additive feature)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from webstudio_backend.api.schemas.product_model import CreateProductModelRequest
from webstudio_backend.infrastructure.database.enums import InventoryStatus


class PurchaseTaxBreakdown(BaseModel):
    subtotal: Decimal | None = None
    discount_amount: Decimal | None = None
    round_off: Decimal | None = None
    cgst_amount: Decimal | None = None
    sgst_amount: Decimal | None = None
    igst_amount: Decimal | None = None
    cess_amount: Decimal | None = None
    grand_total: Decimal | None = None


class PurchaseQueueItem(BaseModel):
    id: int
    supplier_name: str | None
    voucher_date: date | None
    voucher_number: str
    invoice_number: str | None
    reference_number: str | None
    voucher_guid: str
    voucher_type: str | None
    grand_total: Decimal | None
    taxes: PurchaseTaxBreakdown
    status: str
    group_count: int
    imported_group_count: int
    pending_group_count: int


class PurchaseSerialCell(BaseModel):
    serial_number: str
    is_duplicate: bool = False
    existing_status: str | None = None


class PurchaseModelGroup(BaseModel):
    group_key: str
    stock_item_name: str
    quantity: int
    serial_source: str | None
    serials: list[PurchaseSerialCell]
    line_total: Decimal | None = None
    imported: bool = False
    product_model_id: uuid.UUID | None = None
    duplicate_count: int = 0


class PurchaseVoucherDetail(BaseModel):
    id: int
    supplier_name: str | None
    voucher_date: date | None
    voucher_number: str
    invoice_number: str | None
    reference_number: str | None
    voucher_guid: str
    voucher_type: str | None
    narration: str | None
    taxes: PurchaseTaxBreakdown
    grand_total: Decimal | None
    status: str
    groups: list[PurchaseModelGroup]


class MatchModelRequest(BaseModel):
    brand_id: int = Field(gt=0)
    model_number: str = Field(min_length=1, max_length=512)


class MatchedModel(BaseModel):
    id: uuid.UUID
    model_number: str
    model_name: str
    category: str
    is_active: bool
    # "exact"  — normalized model number matches exactly (auto-selectable).
    # "partial" — one model number contains the other (suggestion only, e.g. an
    #   IMS entry with an extra base-model suffix). Never auto-selected.
    match_kind: str = "exact"


class MatchModelResponse(BaseModel):
    normalized_model_number: str
    matches: list[MatchedModel]
    auto_selected_model_id: uuid.UUID | None = None


class MatchAccessoryRequest(BaseModel):
    brand_id: int = Field(gt=0)
    # Free-text query: the Tally stock item name and/or an operator-typed
    # part number or model number. Matched fuzzily against the catalogue.
    query: str = Field(min_length=1, max_length=512)


class AccessoryMatch(BaseModel):
    id: uuid.UUID
    model_number: str
    model_name: str
    part_number: str | None = None
    accessory_kind: str | None = None
    category: str
    is_active: bool
    # 0..1 confidence from the fuzzy accessory matcher.
    score: float


class MatchAccessoryResponse(BaseModel):
    normalized_query: str
    matches: list[AccessoryMatch]
    auto_selected_model_id: uuid.UUID | None = None


class PurchaseImportRequest(BaseModel):
    voucher_id: int
    group_key: str = Field(min_length=1, max_length=512)
    brand_id: int = Field(gt=0)
    mode: str = Field(pattern="^(existing|new)$")
    product_model_id: uuid.UUID | None = None
    new_product_model: CreateProductModelRequest | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    color: str = Field(min_length=1, max_length=64)
    current_location_id: int = Field(gt=0)
    status: InventoryStatus = InventoryStatus.AVAILABLE
    purchase_price: Decimal | None = Field(default=None, ge=0)
    # When true, serials that already exist anywhere in IMS are skipped (reported
    # back as skipped_serials) instead of rejecting the whole import — so the
    # remaining new units can still be imported. Default false keeps the strict
    # legacy behavior (409 on any duplicate).
    skip_existing_serials: bool = False


class PurchaseImportResponse(BaseModel):
    product_model_id: uuid.UUID
    imported_count: int
    voucher_status: str
    group_key: str
    existing_model: bool
    # Serials that were already present in IMS and therefore not re-created.
    skipped_count: int = 0
    skipped_serials: list[str] = Field(default_factory=list)


class PurchaseIgnoreResponse(BaseModel):
    voucher_id: int
    status: str


class PurchaseBackfillRequest(BaseModel):
    """Fetch historical PURCHASE vouchers from Tally into the review queue."""

    from_date: date
    to_date: date | None = None


class PurchaseBackfillResponse(BaseModel):
    fetched: int
    new: int
    from_date: date
    to_date: date | None = None


class PurchaseRefreshResponse(BaseModel):
    voucher_id: int
    status: str
    refreshed: bool = True
