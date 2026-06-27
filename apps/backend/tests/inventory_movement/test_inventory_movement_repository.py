"""InventoryMovement repository tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_movement.conftest import sample_movement_payload
from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    MovementReason,
)
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories import PageParams, SortParam
from webstudio_backend.infrastructure.repositories import (
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemNotFoundError,
    InventoryItemRepository,
    InventoryMovementRepository,
    LocationRepository,
    ProductModelRepository,
    SameLocationMovementError,
    SoldItemCannotMoveError,
    SourceLocationMismatchError,
)


@pytest.mark.asyncio
async def test_movement_create_updates_current_location(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    repository = InventoryMovementRepository(db_session)
    payload = sample_movement_payload(
        inventory_item_id=inventory_item.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
    )

    movement = await repository.create(**payload)

    assert movement.id is not None
    assert movement.movement_reason is MovementReason.STORE_TRANSFER

    refreshed = await InventoryItemRepository(db_session).get_by_id(inventory_item.id)
    assert refreshed is not None
    assert refreshed.current_location_id == to_location.id


@pytest.mark.asyncio
async def test_get_latest_and_list_by_inventory_item(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    repository = InventoryMovementRepository(db_session)
    third_location = await LocationRepository(db_session).create(
        "WEBSTUDIO Multi-brand Store",
        location_type=LocationType.RETAIL_FLOOR,
    )

    first = await repository.create(
        **sample_movement_payload(
            inventory_item_id=inventory_item.id,
            from_location_id=from_location.id,
            to_location_id=to_location.id,
            moved_at=datetime(2026, 6, 27, 9, 0, tzinfo=UTC),
        ),
    )
    inventory_item.current_location_id = to_location.id
    await db_session.flush()

    second = await repository.create(
        **sample_movement_payload(
            inventory_item_id=inventory_item.id,
            from_location_id=to_location.id,
            to_location_id=third_location.id,
            movement_reason=MovementReason.DISPLAY,
            moved_at=datetime(2026, 6, 27, 11, 0, tzinfo=UTC),
        ),
    )

    latest = await repository.get_latest_by_inventory_item(inventory_item.id)
    assert latest is not None
    assert latest.id == second.id

    loaded = await repository.get_by_id(first.id)
    assert loaded is not None
    assert loaded.inventory_item_id == inventory_item.id

    history = await repository.list_by_inventory_item(inventory_item.id, PageParams())
    assert history.total_items == 2


@pytest.mark.asyncio
async def test_list_history_pagination_and_sorting(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
    product_model: ProductModel,
) -> None:
    repository = InventoryMovementRepository(db_session)
    other_item = await InventoryItemRepository(db_session).create(
        serial_number="SN-MOVE-002",
        product_model_id=product_model.id,
        color="Silver",
        current_location_id=from_location.id,
        status=InventoryStatus.AVAILABLE,
    )

    await repository.create(
        **sample_movement_payload(
            inventory_item_id=inventory_item.id,
            from_location_id=from_location.id,
            to_location_id=to_location.id,
            moved_at=datetime(2026, 6, 27, 8, 0, tzinfo=UTC),
        ),
    )
    inventory_item.current_location_id = to_location.id
    await db_session.flush()

    await repository.create(
        **sample_movement_payload(
            inventory_item_id=other_item.id,
            from_location_id=from_location.id,
            to_location_id=to_location.id,
            moved_at=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
        ),
    )

    page = await repository.list_history(
        PageParams(page=1, page_size=1),
        sort_params=[SortParam(field="moved_at", direction="asc")],
    )

    assert page.total_items == 2
    assert len(page.items) == 1
    assert page.items[0].moved_at == datetime(2026, 6, 27, 8, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_same_location_rejected(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
) -> None:
    repository = InventoryMovementRepository(db_session)

    with pytest.raises(SameLocationMovementError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=from_location.id,
                to_location_id=from_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_sold_item_rejected(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    inventory_item.status = InventoryStatus.SOLD
    await db_session.flush()
    repository = InventoryMovementRepository(db_session)

    with pytest.raises(SoldItemCannotMoveError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_missing_inventory_item_rejected(
    db_session: AsyncSession,
    from_location: Location,
    to_location: Location,
) -> None:
    import uuid

    repository = InventoryMovementRepository(db_session)

    with pytest.raises(InventoryItemNotFoundError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=uuid.uuid4(),
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_inactive_location_rejected(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    to_location.is_active = False
    await db_session.flush()
    repository = InventoryMovementRepository(db_session)

    with pytest.raises(InactiveLocationError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_inactive_product_model_rejected(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
    product_model: ProductModel,
) -> None:
    await ProductModelRepository(db_session).archive(product_model)
    repository = InventoryMovementRepository(db_session)

    with pytest.raises(InactiveProductModelError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_source_location_mismatch_rejected(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    repository = InventoryMovementRepository(db_session)

    with pytest.raises(SourceLocationMismatchError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=to_location.id,
                to_location_id=from_location.id,
            ),
        )


@pytest.mark.asyncio
async def test_failed_movement_does_not_persist(
    db_session: AsyncSession,
    inventory_item: InventoryItem,
    from_location: Location,
    to_location: Location,
) -> None:
    repository = InventoryMovementRepository(db_session)
    payload = sample_movement_payload(
        inventory_item_id=inventory_item.id,
        from_location_id=from_location.id,
        to_location_id=to_location.id,
    )
    await repository.create(**payload)

    item_before = await InventoryItemRepository(db_session).get_by_id(inventory_item.id)
    assert item_before is not None
    history_before = await repository.list_history(PageParams())

    with pytest.raises(SourceLocationMismatchError):
        await repository.create(
            **sample_movement_payload(
                inventory_item_id=inventory_item.id,
                from_location_id=from_location.id,
                to_location_id=to_location.id,
            ),
        )

    item_after = await InventoryItemRepository(db_session).get_by_id(inventory_item.id)
    history_after = await repository.list_history(PageParams())

    assert item_after is not None
    assert item_after.current_location_id == item_before.current_location_id
    assert history_after.total_items == history_before.total_items
