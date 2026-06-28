"""Reference data test isolation and auth fixtures."""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.app import create_app
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import get_db_session
from webstudio_backend.infrastructure.database.enums import UserRole
from webstudio_backend.infrastructure.repositories.user_repository import UserRepository
from webstudio_backend.infrastructure.security.password import hash_password
from webstudio_backend.services.setup_service import SetupService

TEST_PASSWORD = "SecurePass123!"
MAIN_ADMIN_USERNAME = "mainadmin"


@pytest_asyncio.fixture(autouse=True)
async def clean_reference_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.audit_logs, webstudio.inventory_items, "
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
async def initialized_system(db_session: AsyncSession) -> None:
    await SetupService(db_session).initialize(
        company_name="WEBSTUDIO",
        main_admin_name="Main Admin",
        username=MAIN_ADMIN_USERNAME,
        password=TEST_PASSWORD,
        confirm_password=TEST_PASSWORD,
    )
    await SetupService(db_session).confirm_recovery_key()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    settings = get_settings().model_copy(update={"jwt_secret": "test-jwt-secret-for-auth-tests-32b!"})
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
async def admin_headers(db_session: AsyncSession, api_client: AsyncClient, initialized_system) -> dict[str, str]:
    await UserRepository(db_session).create(
        username="admin1",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.ADMIN,
        display_name="Admin One",
    )
    return await login_headers(api_client, "admin1", TEST_PASSWORD)


@pytest_asyncio.fixture
async def salesperson_headers(db_session: AsyncSession, api_client: AsyncClient, initialized_system) -> dict[str, str]:
    await UserRepository(db_session).create(
        username="sales1",
        password_hash=hash_password(TEST_PASSWORD),
        role=UserRole.SALESPERSON,
        display_name="Sales One",
    )
    return await login_headers(api_client, "sales1", TEST_PASSWORD)
