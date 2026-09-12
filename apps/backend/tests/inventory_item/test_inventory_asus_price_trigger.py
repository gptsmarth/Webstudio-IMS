"""Manually adding inventory (the non-Tally-import "Add Inventory" path)
must trigger an immediate ASUS live-price refresh when it brings a
previously out-of-stock model back into stock — matching the same trigger
added to the Tally purchase-import path, since both are equally valid ways
stock re-enters circulation.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import InventoryStatus
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.services.inventory_service import InventoryService

pytestmark = pytest.mark.asyncio


async def test_create_item_from_zero_stock_triggers_asus_price_refresh(
    db_session: AsyncSession,
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    admin_actor: AuditActor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import webstudio_backend.services.inventory_service as inventory_service_module

    triggered: list[str] = []
    monkeypatch.setattr(
        inventory_service_module,
        "schedule_asus_price_refresh",
        lambda model_id: triggered.append(str(model_id)),
    )

    service = InventoryService(db_session)
    await service.create_item(
        serial_number="SN-RESTOCK-1",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
        actor=admin_actor,
    )

    assert triggered == [str(product_model.id)]


async def test_create_item_already_in_stock_does_not_retrigger_asus_price_refresh(
    db_session: AsyncSession,
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    admin_actor: AuditActor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adding another unit to a model that already has stock is routine, not
    a "back from zero" event — shouldn't spend a Gemini call every time."""
    import webstudio_backend.services.inventory_service as inventory_service_module

    await InventoryItemRepository(db_session).create(
        serial_number="SN-ALREADY-IN-STOCK",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
    )
    await db_session.commit()

    triggered: list[str] = []
    monkeypatch.setattr(
        inventory_service_module,
        "schedule_asus_price_refresh",
        lambda model_id: triggered.append(str(model_id)),
    )

    service = InventoryService(db_session)
    await service.create_item(
        serial_number="SN-RESTOCK-2",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.AVAILABLE,
        actor=admin_actor,
    )

    assert triggered == []


async def test_create_item_non_available_status_does_not_trigger_asus_price_refresh(
    db_session: AsyncSession,
    brand: Brand,
    location: Location,
    product_model: ProductModel,
    admin_actor: AuditActor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Creating a unit that isn't immediately AVAILABLE (e.g. RECEIVED,
    pending inspection) shouldn't claim the model is sellable-again yet."""
    import webstudio_backend.services.inventory_service as inventory_service_module

    triggered: list[str] = []
    monkeypatch.setattr(
        inventory_service_module,
        "schedule_asus_price_refresh",
        lambda model_id: triggered.append(str(model_id)),
    )

    service = InventoryService(db_session)
    await service.create_item(
        serial_number="SN-RECEIVED-ONLY",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=location.id,
        status=InventoryStatus.RECEIVED,
        actor=admin_actor,
    )

    assert triggered == []
