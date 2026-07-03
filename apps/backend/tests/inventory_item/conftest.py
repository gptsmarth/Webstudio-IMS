"""Inventory item test fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    LocationType,
    StorageType,
    StorageUnit,
    UserRole,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    LocationRepository,
    ProductModelRepository,
)
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.password import hash_password
from webstudio_backend.services.setup_service import SetupService

TEST_PASSWORD = "SecurePass123!"
MAIN_ADMIN_USERNAME = "mainadmin"


@pytest_asyncio.fixture(autouse=True)
async def clean_inventory_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.audit_logs, webstudio.sales, webstudio.inventory_items, "
            "webstudio.product_models, webstudio.locations, webstudio.brands, "
            "webstudio.refresh_tokens, webstudio.users, webstudio.system_settings "
            "RESTART IDENTITY CASCADE",
        ),
    )
    await db_session.execute(
        text(
            """
            INSERT INTO webstudio.system_settings (setting_key, setting_value, value_type, description)
            VALUES
                ('system_initialized', 'false', 'boolean', 'Init flag'),
                ('lockout_threshold', '5', 'integer', 'Lockout threshold'),
                ('lockout_duration_minutes', '15', 'integer', 'Lockout duration')
            """,
        ),
    )
    await db_session.commit()


@pytest_asyncio.fixture
async def brand(db_session: AsyncSession) -> Brand:
    return await BrandRepository(db_session).create("ASUS")


@pytest_asyncio.fixture
async def location(db_session: AsyncSession) -> Location:
    return await LocationRepository(db_session).create(
        "Warehouse",
        location_type=LocationType.WAREHOUSE,
    )


@pytest_asyncio.fixture
async def product_model(db_session: AsyncSession, brand: Brand) -> ProductModel:
    return await ProductModelRepository(db_session).create(
        brand_id=brand.id,
        model_number="X1502ZA-EJ541WS",
        model_name="Vivobook 15",
        cpu="Intel Core i5-1235U",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )


def sample_inventory_payload(
    *,
    product_model_id,
    current_location_id: int,
    serial_number: str = "SN-ASUS-001",
) -> dict[str, object]:
    return {
        "serial_number": serial_number,
        "product_model_id": product_model_id,
        "color": "Black",
        "current_location_id": current_location_id,
        "status": InventoryStatus.AVAILABLE,
    }


@pytest_asyncio.fixture
async def initialized_system(db_session: AsyncSession) -> tuple[object, str]:
    result = await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    await SetupService(db_session).confirm_recovery_key()
    return result.user, result.company_name


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    settings = get_settings().model_copy(
        update={"jwt_secret": "test-jwt-secret-for-auth-tests-32b!"}
    )
    app = create_app(settings)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def login_headers(client: AsyncClient, username: str, password: str) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def main_admin_headers(api_client: AsyncClient, initialized_system) -> dict[str, str]:
    return await login_headers(api_client, MAIN_ADMIN_USERNAME, TEST_PASSWORD)


@pytest_asyncio.fixture
async def admin_headers(
    db_session: AsyncSession, api_client: AsyncClient, initialized_system
) -> dict[str, str]:
    await UserRepository(db_session).create(
        username="admin1",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.ADMIN,
        display_name="Admin One",
    )
    return await login_headers(api_client, "admin1", TEST_PASSWORD)


@pytest_asyncio.fixture
async def salesperson_headers(
    db_session: AsyncSession, api_client: AsyncClient, initialized_system
) -> dict[str, str]:
    main_admin, _ = initialized_system
    await UserRepository(db_session).create(
        username="sales1",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.SALESPERSON,
        display_name="Sales One",
    )
    return await login_headers(api_client, "sales1", TEST_PASSWORD)


@pytest_asyncio.fixture
async def admin_actor(initialized_system) -> AuditActor:
    main_admin, _ = initialized_system
    return AuditActor(user_id=main_admin.id, display_name="Main Admin", role="main_admin")
