"""Report API schemas."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from webstudio_backend.infrastructure.database.enums import (
    AuditAction,
    AuditSource,
    InventoryStatus,
    LocationType,
    NotificationCategory,
    NotificationStatus,
    NotificationType,
    SaleSource,
)
from webstudio_backend.infrastructure.database.repositories.pagination import PageResult
from webstudio_backend.infrastructure.repositories.report_filters import ReportFilters, ReportType
from webstudio_backend.infrastructure.repositories.report_repository import (
    AggregateReportRow,
    AuditReportRow,
    InventoryReportRow,
    NotificationReportRow,
    ReportSummary,
    SalesReportRow,
)


class ReportFiltersApplied(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    purchase_date_from: date | None = None
    purchase_date_to: date | None = None
    brand_id: int | None = None
    location_id: int | None = None
    location_type: LocationType | None = None
    product_model_id: uuid.UUID | None = None
    user_id: int | None = None
    inventory_status: InventoryStatus | None = None
    is_archived: bool | None = None
    serial_number: str | None = None
    color: str | None = None
    notification_status: NotificationStatus | None = None
    notification_type: NotificationType | None = None
    notification_category: NotificationCategory | None = None
    invoice_number: str | None = None
    customer_name: str | None = None
    payment_mode: str | None = None
    sale_source: SaleSource | None = None
    audit_action: AuditAction | None = None
    audit_source: AuditSource | None = None
    actor_role: str | None = None
    search: str | None = None
    sort_field: str | None = None
    sort_direction: str | None = None

    @classmethod
    def from_filters(cls, filters: ReportFilters) -> ReportFiltersApplied:
        return cls(
            date_from=filters.date_from,
            date_to=filters.date_to,
            purchase_date_from=filters.purchase_date_from,
            purchase_date_to=filters.purchase_date_to,
            brand_id=filters.brand_id,
            location_id=filters.location_id,
            location_type=filters.location_type,
            product_model_id=filters.product_model_id,
            user_id=filters.user_id,
            inventory_status=filters.inventory_status,
            is_archived=filters.is_archived,
            serial_number=filters.serial_number,
            color=filters.color,
            notification_status=filters.notification_status,
            notification_type=filters.notification_type,
            notification_category=filters.notification_category,
            invoice_number=filters.invoice_number,
            customer_name=filters.customer_name,
            payment_mode=filters.payment_mode,
            sale_source=filters.sale_source,
            audit_action=filters.audit_action,
            audit_source=filters.audit_source,
            actor_role=filters.actor_role,
            search=filters.search,
            sort_field=filters.sort_field,
            sort_direction=filters.sort_direction,
        )


class ReportSummaryResponse(BaseModel):
    total_rows: int
    by_status: dict[str, int]


class InventoryReportRowResponse(BaseModel):
    serial_number: str
    brand_name: str
    model_number: str
    model_name: str
    color: str
    location_name: str
    status: str
    is_archived: bool
    purchase_date: date | None
    created_at: datetime

    @classmethod
    def from_row(cls, row: InventoryReportRow) -> InventoryReportRowResponse:
        return cls(**asdict(row))


class SalesReportRowResponse(BaseModel):
    serial_number: str
    brand_name: str
    model_number: str
    model_name: str
    location_name: str
    invoice_number: str
    customer_name: str | None
    payment_mode: str | None
    sale_source: str
    sold_at: datetime
    recorded_by_user_id: int | None
    recorded_by_display_name: str | None = None

    @classmethod
    def from_row(cls, row: SalesReportRow) -> SalesReportRowResponse:
        return cls(**asdict(row))


class AggregateReportRowResponse(BaseModel):
    group_id: str
    group_name: str
    available: int
    sold: int
    received: int
    reserved: int
    archived: int
    total: int

    @classmethod
    def from_row(cls, row: AggregateReportRow) -> AggregateReportRowResponse:
        return cls(**asdict(row))


class AuditReportRowResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    action: str
    source: str
    actor_display_name: str | None
    actor_user_id: int | None
    description: str | None
    serial_number: str | None
    created_at: datetime

    @classmethod
    def from_row(cls, row: AuditReportRow) -> AuditReportRowResponse:
        return cls(**asdict(row))


class NotificationReportRowResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    @classmethod
    def from_row(cls, row: NotificationReportRow) -> NotificationReportRowResponse:
        return cls(**asdict(row))


class InventoryReportResponse(BaseModel):
    report_type: ReportType = ReportType.INVENTORY
    generated_at: datetime
    filters: ReportFiltersApplied
    summary: ReportSummaryResponse
    rows: list[InventoryReportRowResponse]


class SalesReportResponse(BaseModel):
    report_type: ReportType = ReportType.SALES
    generated_at: datetime
    filters: ReportFiltersApplied
    rows: list[SalesReportRowResponse]


class AuditReportResponse(BaseModel):
    report_type: ReportType = ReportType.AUDIT
    generated_at: datetime
    filters: ReportFiltersApplied
    rows: list[AuditReportRowResponse]


class NotificationReportResponse(BaseModel):
    report_type: ReportType = ReportType.NOTIFICATION
    generated_at: datetime
    filters: ReportFiltersApplied
    rows: list[NotificationReportRowResponse]


class AggregateReportResponse(BaseModel):
    report_type: ReportType
    generated_at: datetime
    filters: ReportFiltersApplied
    rows: list[AggregateReportRowResponse]


def summary_response(summary: ReportSummary) -> ReportSummaryResponse:
    return ReportSummaryResponse(total_rows=summary.total_rows, by_status=summary.by_status)


def page_meta(page_result: PageResult[Any]) -> dict[str, int]:
    return {
        "page": page_result.page,
        "page_size": page_result.page_size,
        "total_items": page_result.total_items,
        "total_pages": page_result.total_pages,
    }
