"""Tests for accessory product models."""

import pytest

from webstudio_backend.infrastructure.database.enums import AccessoryKind, ProductCategory
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)


@pytest.mark.asyncio
async def test_create_accessory_product_model(db_session, brand) -> None:
    from webstudio_backend.infrastructure.audit.audit_actor import AuditActor

    repo = ProductModelRepository(db_session)
    model = await repo.create(
        brand_id=brand.id,
        category=ProductCategory.ACCESSORY,
        accessory_kind=AccessoryKind.MOUSE,
        part_number="90NB0X02-M0A010",
        model_number="MD100",
        model_name="ASUS MD100 Silent Wireless Mouse",
        actor=AuditActor.system(),
    )
    await db_session.commit()

    assert model.category == ProductCategory.ACCESSORY
    assert model.accessory_kind == AccessoryKind.MOUSE
    assert model.part_number == "90NB0X02-M0A010"
    assert model.cpu is None
    assert model.ram_gb is None
    assert model.storage_value is None


@pytest.mark.asyncio
async def test_laptop_still_requires_cpu(db_session, brand) -> None:
    from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
    from webstudio_backend.infrastructure.repositories.exceptions import RequiredFieldError

    repo = ProductModelRepository(db_session)
    with pytest.raises(RequiredFieldError):
        await repo.create(
            brand_id=brand.id,
            category=ProductCategory.LAPTOP,
            model_number="X1504VA",
            model_name="Test Laptop",
            actor=AuditActor.system(),
        )
