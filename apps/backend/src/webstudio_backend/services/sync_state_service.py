"""Sync state for multi-client offline preparation."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.audit_log import AuditLog
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.notification import Notification
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.sale import Sale
from webstudio_backend.services.platform_info_service import resolve_schema_version


async def build_sync_state(session: AsyncSession, *, app_version: str) -> dict[str, object]:
    now = datetime.now(UTC)
    high_water_marks = {
        "inventory": await _max_timestamp(session, InventoryItem.updated_at),
        "sales": await _max_timestamp(session, Sale.created_at),
        "notifications": await _max_timestamp(session, Notification.updated_at),
        "audit_logs": await _max_timestamp(session, AuditLog.created_at),
        "product_models": await _max_timestamp(session, ProductModel.updated_at),
        "brands": await _max_timestamp(session, Brand.updated_at),
        "locations": await _max_timestamp(session, Location.updated_at),
    }
    return {
        "server_time": now.isoformat(),
        "app_version": app_version,
        "schema_version": await resolve_schema_version(session),
        "sync_token": now.isoformat(),
        "high_water_marks": high_water_marks,
        "poll_interval_seconds": 60,
        "supported_entities": list(high_water_marks.keys()),
        "incremental_sync": {
            "status": "preparation",
            "note": (
                "Use high_water_marks as baseline cursors. "
                "Per-entity delta endpoints will be added in a future release."
            ),
        },
    }


async def _max_timestamp(session: AsyncSession, column) -> str | None:
    result = await session.execute(select(func.max(column)))
    value = result.scalar_one_or_none()
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)
