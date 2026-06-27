"""AuditLog repository tests."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from audit_log.conftest import ADMIN_ACTOR
from webstudio_backend.infrastructure.audit import AuditActor
from webstudio_backend.infrastructure.database.enums import AuditAction, InventoryStatus
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories import PageParams
from webstudio_backend.infrastructure.repositories import (
    AuditLogRepository,
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.audit_log_filters import AuditLogSearchFilters
from webstudio_backend.infrastructure.repositories.exceptions import InventoryItemNotFoundError


@pytest.mark.asyncio
async def test_audit_log_crud(db_session: AsyncSession) -> None:
    repository = AuditLogRepository(db_session)
    created = await repository.create(
        entity_type="brand",
        entity_id="1",
        action=AuditAction.CREATE,
        actor_display_name="Admin",
        actor_role="admin",
        new_value={"name": "ASUS"},
    )
    assert created.id is not None

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.action is AuditAction.CREATE

    page = await repository.list(PageParams(page=1, page_size=10))
    assert page.total_items >= 1


@pytest.mark.asyncio
async def test_automatic_inventory_create_audit(
    db_session: AsyncSession,
    inventory_item,
) -> None:
    repository = AuditLogRepository(db_session)
    result = await repository.get_by_inventory_item(
        inventory_item.id,
        PageParams(page=1, page_size=10),
    )
    assert result.total_items == 1
    entry = result.items[0]
    assert entry.action is AuditAction.CREATE
    assert entry.actor_display_name == ADMIN_ACTOR.display_name
    assert entry.new_value is not None
    assert entry.new_value.get("serial_number") == "SN-LIFECYCLE-001"
    assert entry.new_value.get("current_location") == "Warehouse"


@pytest.mark.asyncio
async def test_audit_descriptions(
    db_session: AsyncSession,
    inventory_item,
    store: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.update(inventory_item, current_location_id=store.id, actor=ADMIN_ACTOR)

    audit_repository = AuditLogRepository(db_session)
    result = await audit_repository.get_by_inventory_item(
        inventory_item.id,
        PageParams(page=1, page_size=10),
    )
    create_entry = next(entry for entry in result.items if entry.action is AuditAction.CREATE)
    move_entry = next(
        entry for entry in result.items if entry.action is AuditAction.LOCATION_CHANGE
    )
    assert create_entry.description == "Inventory item added (serial: SN-LIFECYCLE-001)"
    assert move_entry.description == "Location changed from Warehouse to ASUS Store"


@pytest.mark.asyncio
async def test_audit_pagination(
    db_session: AsyncSession,
    inventory_item,
    store: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.update(inventory_item, current_location_id=store.id, actor=ADMIN_ACTOR)

    audit_repository = AuditLogRepository(db_session)
    page_one = await audit_repository.get_by_inventory_item(
        inventory_item.id,
        PageParams(page=1, page_size=1),
    )
    page_two = await audit_repository.get_by_inventory_item(
        inventory_item.id,
        PageParams(page=2, page_size=1),
    )
    assert page_one.total_items == 2
    assert page_one.total_pages == 2
    assert len(page_one.items) == 1
    assert len(page_two.items) == 1
    assert page_one.items[0].id != page_two.items[0].id


@pytest.mark.asyncio
async def test_automatic_location_change_audit(
    db_session: AsyncSession,
    inventory_item,
    store: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.update(
        inventory_item,
        current_location_id=store.id,
        actor=ADMIN_ACTOR,
    )

    audit_repository = AuditLogRepository(db_session)
    result = await audit_repository.search(
        AuditLogSearchFilters(action=AuditAction.LOCATION_CHANGE),
        PageParams(page=1, page_size=10),
    )
    assert result.total_items == 1
    entry = result.items[0]
    assert entry.field_name == "current_location"
    assert entry.old_value is not None
    assert entry.new_value is not None
    assert entry.old_value["current_location"] == "Warehouse"
    assert entry.new_value["current_location"] == "ASUS Store"


@pytest.mark.asyncio
async def test_automatic_status_change_audit(
    db_session: AsyncSession,
    inventory_item,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.update(
        inventory_item,
        status=InventoryStatus.SOLD,
        actor=ADMIN_ACTOR,
    )

    audit_repository = AuditLogRepository(db_session)
    result = await audit_repository.search(
        AuditLogSearchFilters(action=AuditAction.STATUS_CHANGE),
        PageParams(page=1, page_size=10),
    )
    assert result.total_items == 1
    entry = result.items[0]
    assert entry.old_value is not None
    assert entry.new_value is not None
    assert entry.old_value["status"] == "available"
    assert entry.new_value["status"] == "sold"


@pytest.mark.asyncio
async def test_serial_number_lifecycle_order(
    db_session: AsyncSession,
    inventory_item,
    store: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.update(inventory_item, current_location_id=store.id, actor=ADMIN_ACTOR)
    await repository.update(inventory_item, status=InventoryStatus.SOLD, actor=ADMIN_ACTOR)

    audit_repository = AuditLogRepository(db_session)
    lifecycle = await audit_repository.get_by_serial_number(
        "SN-LIFECYCLE-001",
        PageParams(page=1, page_size=20),
    )
    assert lifecycle.total_items == 3
    actions = [entry.action for entry in lifecycle.items]
    assert actions == [
        AuditAction.CREATE,
        AuditAction.LOCATION_CHANGE,
        AuditAction.STATUS_CHANGE,
    ]


@pytest.mark.asyncio
async def test_search_by_brand(
    db_session: AsyncSession,
    product_model: ProductModel,
    inventory_item,
    brand,
) -> None:
    audit_repository = AuditLogRepository(db_session)
    result = await audit_repository.search(
        AuditLogSearchFilters(brand_id=brand.id),
        PageParams(page=1, page_size=20),
    )
    assert result.total_items >= 1


@pytest.mark.asyncio
async def test_search_serial_not_found(db_session: AsyncSession) -> None:
    audit_repository = AuditLogRepository(db_session)
    with pytest.raises(InventoryItemNotFoundError):
        await audit_repository.get_by_serial_number(
            "MISSING-SERIAL",
            PageParams(page=1, page_size=10),
        )


@pytest.mark.asyncio
async def test_audit_rollback_not_persisted(
    db_session: AsyncSession,
    product_model: ProductModel,
    warehouse: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.create(
        serial_number="SN-ROLLBACK-001",
        product_model_id=product_model.id,
        color="Black",
        current_location_id=warehouse.id,
        status=InventoryStatus.AVAILABLE,
        actor=ADMIN_ACTOR,
    )
    await db_session.rollback()

    audit_repository = AuditLogRepository(db_session)
    result = await audit_repository.search(
        AuditLogSearchFilters(serial_number="SN-ROLLBACK-001"),
        PageParams(page=1, page_size=10),
    )
    assert result.total_items == 0
