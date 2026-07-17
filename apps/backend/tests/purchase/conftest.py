"""Purchase Import test fixtures (additive feature).

Builds a Tally company sync + purchase voucher directly in the DB so tests can
exercise the queue projection, model matching, and transactional import without
touching the Sales sync path.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
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
    LocationType,
    StorageType,
    StorageUnit,
    TallyPurchaseStatus,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.models.tally_company_sync import TallyCompanySync
from webstudio_backend.infrastructure.database.models.tally_purchase_line import TallyPurchaseLine
from webstudio_backend.infrastructure.database.models.tally_purchase_voucher import (
    TallyPurchaseVoucher,
)
from webstudio_backend.infrastructure.repositories import (
    BrandRepository,
    LocationRepository,
    ProductModelRepository,
)
from webstudio_backend.services.setup_service import SetupService

TEST_PASSWORD = "SecurePass123!"
MAIN_ADMIN_USERNAME = "mainadmin"


@pytest_asyncio.fixture(autouse=True)
async def clean_purchase_tables(db_session: AsyncSession) -> None:
    await db_session.execute(
        text(
            "TRUNCATE TABLE webstudio.tally_purchase_line, webstudio.tally_purchase_voucher, "
            "webstudio.tally_company_sync, webstudio.audit_logs, webstudio.sales, "
            "webstudio.inventory_items, webstudio.product_models, webstudio.locations, "
            "webstudio.brands, webstudio.refresh_tokens, webstudio.users, "
            "webstudio.system_settings RESTART IDENTITY CASCADE",
        ),
    )
    await db_session.execute(
        text(
            """
            INSERT INTO webstudio.system_settings
                (setting_key, setting_value, value_type, description)
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
        model_number="F1504FA-BQ2113WS",
        model_name="Vivobook 15",
        cpu="Intel Core i5-1235U",
        ram_gb=16,
        storage_value=Decimal("512"),
        storage_unit=StorageUnit.GB,
        storage_type=StorageType.SSD,
    )


@pytest_asyncio.fixture
async def purchase_voucher(db_session: AsyncSession) -> TallyPurchaseVoucher:
    """A pending voucher with one laptop group (2 serials) and one accessory
    group (no serials). Tally sends the brand-prefixed stock item name."""
    now = datetime.now(UTC)
    company = TallyCompanySync(company_name="Test Co")
    db_session.add(company)
    await db_session.flush()

    voucher = TallyPurchaseVoucher(
        tally_company_sync_id=company.id,
        tally_voucher_guid="guid-purchase-66",
        tally_voucher_number="66",
        printed_invoice_number="INV-66",
        reference_number="REF-66",
        voucher_type="Purchase",
        voucher_date=date(2026, 1, 15),
        supplier_name="Acme Distributors",
        subtotal=Decimal("100000.00"),
        cgst_amount=Decimal("9000.00"),
        sgst_amount=Decimal("9000.00"),
        grand_total=Decimal("118000.00"),
        status=TallyPurchaseStatus.PENDING,
        first_seen_at=now,
        last_seen_at=now,
    )
    voucher.lines = [
        TallyPurchaseLine(
            line_index=0,
            stock_item_name="ASUS F1504FA-BQ2113WS",
            group_key="ASUS F1504FA-BQ2113WS",
            quantity="2",
            serials_json=json.dumps(["SNPUR001", "SNPUR002"]),
            serial_source="tally",
            line_total=Decimal("100000.00"),
        ),
        TallyPurchaseLine(
            line_index=1,
            stock_item_name="ASUS Carry Case",
            group_key="ASUS Carry Case",
            quantity="2",
            serials_json=None,
            serial_source=None,
            line_total=Decimal("2000.00"),
        ),
    ]
    db_session.add(voucher)
    await db_session.commit()
    await db_session.refresh(voucher)
    return voucher


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
async def admin_actor(initialized_system) -> AuditActor:
    main_admin, _ = initialized_system
    return AuditActor(user_id=main_admin.id, display_name="Main Admin", role="main_admin")


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncClient:
    settings = get_settings().model_copy(
        update={"jwt_secret": "test-jwt-secret-for-purchase-tests-32b!"}
    )
    app = create_app(settings)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture
async def main_admin_headers(api_client: AsyncClient, initialized_system) -> dict[str, str]:
    response = await api_client.post(
        "/api/v1/auth/login",
        json={"username": MAIN_ADMIN_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
