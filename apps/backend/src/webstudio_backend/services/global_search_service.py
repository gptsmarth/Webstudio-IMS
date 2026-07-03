"""Unified global search across catalogue and operational entities."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams
from webstudio_backend.infrastructure.repositories.inventory_item_filters import (
    InventorySearchFilters,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)

DEFAULT_LIMIT = 10
MAX_LIMIT = 25
VALID_TYPES = frozenset({"inventory", "brand", "location", "product_model"})


async def global_search(
    session: AsyncSession,
    *,
    query: str,
    types: list[str] | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict[str, object]:
    term = query.strip()
    if not term:
        return {"query": "", "results": []}

    selected = {item.strip().lower() for item in (types or VALID_TYPES) if item.strip()}
    selected &= VALID_TYPES
    if not selected:
        selected = set(VALID_TYPES)

    per_type_limit = max(1, min(limit, MAX_LIMIT))
    results: list[dict[str, object]] = []

    if "inventory" in selected:
        repo = InventoryItemRepository(session)
        page = await repo.search(
            InventorySearchFilters(search=term),
            PageParams(page=1, page_size=per_type_limit),
        )
        for row in page.items:
            results.append(
                {
                    "type": "inventory",
                    "id": str(row.item.id),
                    "title": row.item.serial_number,
                    "subtitle": f"{row.brand.name} {row.product_model.model_number}",
                    "href": f"/inventory/{row.item.id}",
                },
            )

    prefix = f"{term}%"
    if "brand" in selected:
        statement = (
            select(Brand)
            .where(or_(Brand.name.ilike(prefix), Brand.short_name.ilike(prefix)))
            .order_by(Brand.display_order, Brand.name)
            .limit(per_type_limit)
        )
        for brand in (await session.execute(statement)).scalars().all():
            results.append(
                {
                    "type": "brand",
                    "id": str(brand.id),
                    "title": brand.name,
                    "subtitle": brand.short_name,
                    "href": f"/catalogue/brands/{brand.id}",
                },
            )

    if "location" in selected:
        statement = (
            select(Location)
            .where(Location.name.ilike(prefix))
            .order_by(Location.name)
            .limit(per_type_limit)
        )
        for location in (await session.execute(statement)).scalars().all():
            results.append(
                {
                    "type": "location",
                    "id": str(location.id),
                    "title": location.name,
                    "subtitle": location.location_type.value if location.location_type else None,
                    "href": f"/catalogue/locations/{location.id}",
                },
            )

    if "product_model" in selected:
        statement = (
            select(ProductModel, Brand.name)
            .join(Brand, ProductModel.brand_id == Brand.id)
            .where(
                or_(
                    ProductModel.model_number.ilike(prefix),
                    ProductModel.model_name.ilike(prefix),
                    Brand.name.ilike(prefix),
                ),
            )
            .order_by(ProductModel.model_name, ProductModel.model_number)
            .limit(per_type_limit)
        )
        for model, brand_name in (await session.execute(statement)).all():
            results.append(
                {
                    "type": "product_model",
                    "id": str(model.id),
                    "title": model.model_number,
                    "subtitle": f"{brand_name} — {model.model_name}",
                    "href": f"/catalogue/models/{model.id}",
                },
            )

    return {"query": term, "results": results[: per_type_limit * len(selected)]}
