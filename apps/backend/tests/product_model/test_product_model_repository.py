"""ProductModel repository tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from product_model.conftest import sample_product_model_payload
from webstudio_backend.infrastructure.database.enums import (
    ProductModelStatus,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.repositories import PageParams, SortParam
from webstudio_backend.infrastructure.repositories import (
    DuplicateModelNumberError,
    InvalidFieldValueError,
    ProductModelRepository,
    RequiredFieldError,
)


@pytest.mark.asyncio
async def test_product_model_crud(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)

    created = await repository.create(**payload)
    assert created.id is not None
    assert created.status is ProductModelStatus.ACTIVE

    loaded = await repository.get_by_id(created.id)
    assert loaded is not None
    assert loaded.model_name == "Vivobook 15"

    updated = await repository.update(loaded, model_name="Vivobook 15 OLED")
    assert updated.model_name == "Vivobook 15 OLED"

    from sqlalchemy import text

    result = await db_session.execute(
        text(
            "SELECT COUNT(*) FROM webstudio.audit_logs "
            "WHERE entity_type = 'product_model' AND entity_id = :id",
        ),
        {"id": str(created.id)},
    )
    assert int(result.scalar_one()) >= 2


@pytest.mark.asyncio
async def test_duplicate_model_number_rejected(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)
    await repository.create(**payload)

    with pytest.raises(DuplicateModelNumberError):
        await repository.create(**payload)


@pytest.mark.asyncio
async def test_same_model_number_allowed_for_different_brands(db_session: AsyncSession) -> None:
    repository = ProductModelRepository(db_session)
    asus = await repository._session.get(Brand, (await _create_brand(db_session, "ASUS")).id)
    hp = await _create_brand(db_session, "HP")

    first = await repository.create(**sample_product_model_payload(asus.id))
    second = await repository.create(**sample_product_model_payload(hp.id))

    assert first.model_number == second.model_number
    assert first.brand_id != second.brand_id


@pytest.mark.asyncio
async def test_archive_and_restore(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    model = await repository.create(**sample_product_model_payload(brand.id))

    archived = await repository.archive(model)
    assert archived.status is ProductModelStatus.ARCHIVED

    restored = await repository.restore(archived)
    assert restored.status is ProductModelStatus.ACTIVE


@pytest.mark.asyncio
async def test_force_delete_removes_model(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    model = await repository.create(**sample_product_model_payload(brand.id))

    await repository.force_delete(model)
    assert await repository.get_by_id(model.id) is None


@pytest.mark.asyncio
async def test_exists(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)

    assert await repository.exists(brand.id, payload["model_number"]) is False
    await repository.create(**payload)
    assert await repository.exists(brand.id, payload["model_number"]) is True


@pytest.mark.asyncio
async def test_find_active_and_archived(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    active = await repository.create(**sample_product_model_payload(brand.id))
    archived_payload = sample_product_model_payload(brand.id)
    archived_payload["model_number"] = "X1502ZA-ARCHIVE"
    archived = await repository.create(**archived_payload)
    await repository.archive(archived)

    active_page = await repository.find_active(PageParams())
    archived_page = await repository.find_archived(PageParams())

    assert any(item.id == active.id for item in active_page.items)
    assert any(item.id == archived.id for item in archived_page.items)


@pytest.mark.asyncio
async def test_find_by_brand_pagination_and_sorting(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    for model_number in ("AAA-001", "BBB-002", "CCC-003"):
        payload = sample_product_model_payload(brand.id)
        payload["model_number"] = model_number
        await repository.create(**payload)

    page = await repository.find_by_brand(
        brand.id,
        PageParams(page=1, page_size=2),
        sort_params=[SortParam(field="model_number", direction="asc")],
    )

    assert page.total_items == 3
    assert len(page.items) == 2
    assert page.items[0].model_number <= page.items[1].model_number


@pytest.mark.asyncio
async def test_search_by_model_number_and_name(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)
    await repository.create(**payload)

    by_number = await repository.search_by_model_number("X1502", PageParams())
    by_name = await repository.search_by_model_name("Vivobook", PageParams())

    assert by_number.total_items == 1
    assert by_name.total_items == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "payload_override"),
    [
        ("model_number", {"model_number": "   "}),
        ("model_name", {"model_name": ""}),
        ("cpu", {"cpu": " "}),
        ("ram_gb", {"ram_gb": 0}),
        ("storage_value", {"storage_value": Decimal("0")}),
    ],
)
async def test_invalid_data_validation(
    db_session: AsyncSession,
    brand: Brand,
    field: str,
    payload_override: dict[str, object],
) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)
    payload.update(payload_override)

    with pytest.raises((RequiredFieldError, InvalidFieldValueError)):
        await repository.create(**payload)


@pytest.mark.asyncio
async def test_create_rolls_back_on_failure(db_session: AsyncSession, brand: Brand) -> None:
    repository = ProductModelRepository(db_session)
    payload = sample_product_model_payload(brand.id)
    await repository.create(**payload)

    with pytest.raises(DuplicateModelNumberError):
        await repository.create(**payload)

    await db_session.rollback()
    assert await repository.exists(brand.id, str(payload["model_number"])) is False


async def _create_brand(db_session: AsyncSession, name: str) -> Brand:
    from webstudio_backend.infrastructure.repositories import BrandRepository

    return await BrandRepository(db_session).create(name)
