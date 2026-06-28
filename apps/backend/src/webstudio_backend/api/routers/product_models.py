"""ProductModel API endpoints."""

from __future__ import annotations

from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.schemas.product_model import (
    CreateProductModelRequest,
    ProductModelResponse,
    ProductModelSpecLookupRequest,
    ProductModelSpecLookupResponse,
    UpdateProductModelRequest,
    UpdateSellingPriceRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.config import get_settings
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import ProductModelStatus, UserRole
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateModelNumberError
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.gemini_config import resolve_gemini_credentials
from webstudio_backend.services.gemini_spec_service import GeminiLookupError, GeminiSpecService

router = APIRouter(prefix="/api/v1/product-models", tags=["product-models"])

ProductModelsReadDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:read"))]
ProductModelsWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:write"))]
ProductModelsArchiveDep = Annotated[AuthenticatedUser, Depends(require_permission("product_models:archive"))]
ProductModelsSellingPriceDep = Annotated[
    AuthenticatedUser,
    Depends(require_permission("product_models:selling_price:write")),
]
InventoryWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("inventory:write"))]


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        meta=None,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


def _can_view_purchase_price(current: AuthenticatedUser) -> bool:
    return current.user.role in {UserRole.MAIN_ADMIN, UserRole.ADMIN}


def _model_payload(pm, *, brand_name: str | None, current: AuthenticatedUser) -> dict:
    include_purchase = _can_view_purchase_price(current)
    response = ProductModelResponse.from_model(
        pm,
        brand_name=brand_name,
        include_purchase_price=include_purchase,
    )
    exclude = set() if include_purchase else {"purchase_price"}
    return response.model_dump(exclude=exclude)


@router.get("")
async def list_product_models(
    request: Request,
    current: ProductModelsReadDep,
    brand_id: int | None = None,
    active: bool | None = None,
    archived: bool | None = None,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    statement = select(ProductModel, Brand.name).outerjoin(Brand, ProductModel.brand_id == Brand.id)

    if brand_id is not None:
        statement = statement.where(ProductModel.brand_id == brand_id)
    if active is not None:
        if active:
            statement = statement.where(ProductModel.status == ProductModelStatus.ACTIVE)
        else:
            statement = statement.where(ProductModel.status != ProductModelStatus.ACTIVE)
    if archived is not None:
        if archived:
            statement = statement.where(ProductModel.status == ProductModelStatus.ARCHIVED)
        else:
            statement = statement.where(ProductModel.status != ProductModelStatus.ARCHIVED)

    result = await db_session.execute(statement)
    product_models = result.all()

    # Sort product models by model_name, then by model_number
    sorted_models = sorted(product_models, key=lambda row: (row[0].model_name.lower(), row[0].model_number.lower()))

    data = [
        _model_payload(row[0], brand_name=row[1], current=current)
        for row in sorted_models
    ]
    return _envelope(request, data)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product_model(
    request: Request,
    body: CreateProductModelRequest,
    current: ProductModelsWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    # Validate brand exists and is active
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(body.brand_id)
    if not brand:
        raise AppError(
            "VALIDATION_ERROR",
            f"Brand with ID {body.brand_id} does not exist",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not brand.is_active:
        raise AppError(
            "VALIDATION_ERROR",
            f"Brand '{brand.name}' is archived and cannot be referenced by new product models",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    repo = ProductModelRepository(db_session)
    try:
        pm = await repo.create(
            brand_id=body.brand_id,
            model_number=body.model_number,
            model_name=body.model_name,
            cpu=body.cpu,
            gpu=body.gpu,
            ram_gb=body.ram_gb,
            storage_value=body.storage_value,
            storage_unit=body.storage_unit,
            storage_type=body.storage_type,
            status=body.status,
            display=body.display,
            color_options=body.color_options,
            product_image_url=body.product_image_url,
            search_aliases=body.search_aliases,
            notes=body.notes,
            purchase_price=body.purchase_price,
            selling_price=body.selling_price,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, _model_payload(pm, brand_name=brand.name, current=current))
    except DuplicateModelNumberError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


@router.get("/{model_id}")
async def get_product_model(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(pm.brand_id)
    brand_name = brand.name if brand else None
    return _envelope(request, _model_payload(pm, brand_name=brand_name, current=current))


@router.patch("/{model_id}")
async def update_product_model(
    request: Request,
    model_id: uuid.UUID,
    body: UpdateProductModelRequest,
    current: ProductModelsWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Validate brand if it is being updated
    if body.brand_id is not None and body.brand_id != pm.brand_id:
        brand_repo = BrandRepository(db_session)
        brand = await brand_repo.get_by_id(body.brand_id)
        if not brand:
            raise AppError(
                "VALIDATION_ERROR",
                f"Brand with ID {body.brand_id} does not exist",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not brand.is_active:
            raise AppError(
                "VALIDATION_ERROR",
                f"Brand '{brand.name}' is archived and cannot be referenced",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    fields_set = body.model_fields_set
    try:
        updated = await repo.update(
            pm,
            model_number=body.model_number,
            model_name=body.model_name,
            cpu=body.cpu,
            gpu=body.gpu,
            ram_gb=body.ram_gb,
            storage_value=body.storage_value,
            storage_unit=body.storage_unit,
            storage_type=body.storage_type,
            display=body.display,
            color_options=body.color_options,
            product_image_url=body.product_image_url,
            search_aliases=body.search_aliases,
            notes=body.notes,
            purchase_price=body.purchase_price,
            set_purchase_price="purchase_price" in fields_set,
            selling_price=body.selling_price,
            set_selling_price="selling_price" in fields_set,
            actor=_actor(current),
        )
        if body.brand_id is not None and body.brand_id != pm.brand_id:
            # Note: Brand updates are handled separately since we don't have update_brand_id
            # directly, let's assign and record it!
            old_brand_id = updated.brand_id
            updated.brand_id = body.brand_id
            from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
            await AuditRecorder(db_session).record_product_model_field_update(
                updated,
                field_name="brand_id",
                old_value={"brand_id": old_brand_id},
                new_value={"brand_id": body.brand_id},
                actor=_actor(current),
            )

        await db_session.commit()
        brand_repo = BrandRepository(db_session)
        brand = await brand_repo.get_by_id(updated.brand_id)
        brand_name = brand.name if brand else None
        return _envelope(request, _model_payload(updated, brand_name=brand_name, current=current))
    except DuplicateModelNumberError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


@router.patch("/{model_id}/selling-price")
async def update_product_model_selling_price(
    request: Request,
    model_id: uuid.UUID,
    body: UpdateSellingPriceRequest,
    current: ProductModelsSellingPriceDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    updated = await repo.update(
        pm,
        selling_price=body.selling_price,
        set_selling_price=True,
        actor=_actor(current),
    )
    await db_session.commit()
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(updated.brand_id)
    brand_name = brand.name if brand else None
    return _envelope(request, _model_payload(updated, brand_name=brand_name, current=current))


@router.post("/{model_id}/archive")
async def archive_product_model(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsArchiveDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    updated = await repo.archive(pm, actor=_actor(current))
    await db_session.commit()
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(updated.brand_id)
    brand_name = brand.name if brand else None
    return _envelope(request, _model_payload(updated, brand_name=brand_name, current=current))


@router.post("/{model_id}/restore")
async def restore_product_model(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsArchiveDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    updated = await repo.restore(pm, actor=_actor(current))
    await db_session.commit()
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(updated.brand_id)
    brand_name = brand.name if brand else None
    return _envelope(request, _model_payload(updated, brand_name=brand_name, current=current))


@router.post("/spec-lookup")
async def lookup_product_model_spec(
    request: Request,
    body: ProductModelSpecLookupRequest,
    current: InventoryWriteDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    del current
    api_key, model = await resolve_gemini_credentials(db_session, app_settings)
    service = GeminiSpecService(app_settings, api_key=api_key, model=model)
    if not service.is_configured:
        raise AppError(
            "SERVICE_UNAVAILABLE",
            "Gemini API is not configured. Add your API key in System Settings → Integrations.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    try:
        result = await service.lookup_laptop_spec(
            body.model_number,
            model_name=body.model_name,
            brand_name=body.brand_name,
        )
    except GeminiLookupError as exc:
        status_code = status.HTTP_404_NOT_FOUND
        if exc.code == "RATE_LIMITED":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif exc.code == "SERVICE_UNAVAILABLE":
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code == "API_ERROR":
            status_code = status.HTTP_502_BAD_GATEWAY
        raise AppError(exc.code, exc.message, status_code=status_code) from exc

    response = ProductModelSpecLookupResponse(
        model_name=result["model_name"],
        cpu=result["cpu"],
        gpu=result.get("gpu"),
        ram_gb=result["ram_gb"],
        storage_value=result["storage_value"],
        storage_unit=result["storage_unit"],
        storage_type=result["storage_type"],
        display=result.get("display"),
        color_options=result.get("color_options"),
        product_image_url=result.get("product_image_url"),
        notes=result.get("notes"),
        source=result.get("source", "gemini"),
    )
    return _envelope(request, response.model_dump())
