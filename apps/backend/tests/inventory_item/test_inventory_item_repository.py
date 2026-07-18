"""InventoryItem repository tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from inventory_item.conftest import sample_inventory_payload
from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories import PageParams, SortParam
from webstudio_backend.infrastructure.repositories import (
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InventoryItemDeleteNotAllowedError,
    InventoryItemRepository,
    LocationRepository,
    ProductModelRepository,
    RequiredFieldError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_filters import (
    InventorySearchFilters,
)


@pytest.mark.asyncio
async def test_inventory_item_crud(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    payload = sample_inventory_payload(
        product_model_id=product_model.id,
        current_location_id=location.id,
    )

    created = await repository.create(**payload)
    assert created.id is not None

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.serial_number == "SN-ASUS-001"

    by_serial = await repository.find_by_serial_number("SN-ASUS-001")
    assert by_serial is not None
    assert by_serial.id == created.id

    updated = await repository.update(loaded, color="Silver")
    assert updated.color == "Silver"

    result = await db_session.execute(
        text("SELECT COUNT(*) FROM webstudio.audit_logs WHERE inventory_item_id = :id"),
        {"id": created.id},
    )
    assert int(result.scalar_one()) >= 1


@pytest.mark.asyncio
async def test_duplicate_serial_number_rejected(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    payload = sample_inventory_payload(
        product_model_id=product_model.id,
        current_location_id=location.id,
    )
    await repository.create(**payload)

    with pytest.raises(DuplicateSerialNumberError):
        await repository.create(**payload)


@pytest.mark.asyncio
async def test_required_field_validation(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)

    with pytest.raises(RequiredFieldError):
        await repository.create(
            serial_number="  ",
            product_model_id=product_model.id,
            color="Black",
            current_location_id=location.id,
            status=InventoryStatus.AVAILABLE,
        )


@pytest.mark.asyncio
async def test_inactive_product_model_rejected(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await ProductModelRepository(db_session).archive(product_model)

    with pytest.raises(InactiveProductModelError):
        await repository.create(
            **sample_inventory_payload(
                product_model_id=product_model.id,
                current_location_id=location.id,
            ),
        )


@pytest.mark.asyncio
async def test_inactive_location_rejected(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    location.is_active = False
    await db_session.flush()

    with pytest.raises(InactiveLocationError):
        await repository.create(
            **sample_inventory_payload(
                product_model_id=product_model.id,
                current_location_id=location.id,
            ),
        )


@pytest.mark.asyncio
async def test_search_and_filters(
    db_session: AsyncSession,
    brand: Brand,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    await repository.create(
        **sample_inventory_payload(
            product_model_id=product_model.id,
            current_location_id=location.id,
            serial_number="SN-FILTER-001",
        ),
    )
    other_location = await LocationRepository(db_session).create(
        "Store",
        location_type=LocationType.RETAIL_FLOOR,
    )
    await repository.create(
        **sample_inventory_payload(
            product_model_id=product_model.id,
            current_location_id=other_location.id,
            serial_number="SN-FILTER-002",
        ),
    )

    by_brand = await repository.filter_by_brand(brand.id, PageParams())
    by_model = await repository.filter_by_product_model(product_model.id, PageParams())
    by_color = await repository.filter_by_color("Black", PageParams())
    by_location = await repository.filter_by_location(location.id, PageParams())
    by_status = await repository.filter_by_status(InventoryStatus.AVAILABLE, PageParams())
    by_search = await repository.search(
        InventorySearchFilters(search="SN-FILTER"),
        PageParams(),
    )
    # Serial search must match fragments anywhere in the serial, not just prefixes.
    by_partial_serial = await repository.search(
        InventorySearchFilters(search="filter-002"),
        PageParams(),
    )

    assert by_brand.total_items == 2
    assert by_model.total_items == 2
    assert by_color.total_items == 2
    assert by_location.total_items == 1
    assert by_status.total_items == 2
    assert by_search.total_items == 2
    assert by_partial_serial.total_items == 1
    assert by_partial_serial.items[0].item.serial_number == "SN-FILTER-002"


@pytest.mark.asyncio
async def test_pagination_and_sorting(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    for index in range(3):
        await repository.create(
            **sample_inventory_payload(
                product_model_id=product_model.id,
                current_location_id=location.id,
                serial_number=f"SN-SORT-{index:03d}",
            ),
        )

    page = await repository.search(
        InventorySearchFilters(),
        PageParams(page=1, page_size=2),
        sort_params=[SortParam(field="serial_number", direction="asc")],
    )

    assert page.total_items == 3
    assert len(page.items) == 2
    assert page.items[0].item.serial_number <= page.items[1].item.serial_number


@pytest.mark.asyncio
async def test_delete_guard_blocks_sold_item(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    item = await repository.create(
        **sample_inventory_payload(
            product_model_id=product_model.id,
            current_location_id=location.id,
        ),
    )
    item.status = InventoryStatus.SOLD
    await db_session.flush()

    with pytest.raises(InventoryItemDeleteNotAllowedError):
        await repository.delete(item)


@pytest.mark.asyncio
async def test_delete_guard_blocks_references(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    item = await repository.create(
        **sample_inventory_payload(
            product_model_id=product_model.id,
            current_location_id=location.id,
        ),
    )

    with (
        patch.object(repository, "_has_audit_references", AsyncMock(return_value=True)),
        pytest.raises(InventoryItemDeleteNotAllowedError),
    ):
        await repository.delete(item)


@pytest.mark.asyncio
async def test_create_rolls_back_on_failure(
    db_session: AsyncSession,
    product_model: ProductModel,
    location: Location,
) -> None:
    repository = InventoryItemRepository(db_session)
    payload = sample_inventory_payload(
        product_model_id=product_model.id,
        current_location_id=location.id,
    )
    await repository.create(**payload)

    with pytest.raises(DuplicateSerialNumberError):
        await repository.create(**payload)

    await db_session.rollback()
    assert await repository.find_by_serial_number("SN-ASUS-001") is None
