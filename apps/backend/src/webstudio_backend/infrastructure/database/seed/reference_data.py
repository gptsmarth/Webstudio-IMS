"""Idempotent development seed data for reference entities."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.enums import LocationType
from webstudio_backend.infrastructure.database.session import init_db, session_scope
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository

DEFAULT_BRANDS: tuple[str, ...] = ("ASUS", "HP", "Dell", "Lenovo", "Acer", "MSI")

DEFAULT_LOCATIONS: tuple[tuple[str, LocationType], ...] = (
    ("Warehouse", LocationType.WAREHOUSE),
    ("Store", LocationType.RETAIL_FLOOR),
    ("Service Area", LocationType.OTHER),
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    brands_created: int
    locations_created: int


async def seed_reference_data(session: AsyncSession) -> SeedResult:
    brand_repository = BrandRepository(session)
    location_repository = LocationRepository(session)

    brands_created = 0
    for name in DEFAULT_BRANDS:
        if await brand_repository.get_by_name(name) is None:
            await brand_repository.create(name)
            brands_created += 1

    locations_created = 0
    for name, location_type in DEFAULT_LOCATIONS:
        if await location_repository.get_by_name(name) is None:
            await location_repository.create(name, location_type=location_type)
            locations_created += 1

    return SeedResult(
        brands_created=brands_created,
        locations_created=locations_created,
    )


async def run_seed() -> SeedResult:
    await init_db(get_settings())
    async with session_scope() as session:
        result = await seed_reference_data(session)
    return result


def main() -> None:
    result = asyncio.run(run_seed())
    print(
        "Reference data seed complete:",
        f"brands_created={result.brands_created},",
        f"locations_created={result.locations_created}",
    )


if __name__ == "__main__":
    main()
