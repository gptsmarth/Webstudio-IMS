"""ProductModel API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.catalogue_errors import raise_catalogue_deletion_error
from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    ProductModelsCreateDep,
    ProductModelsDeleteDep,
    ProductModelsEditDep,
    ProductModelsLivePriceRefreshDep,
    ProductModelsOrInventoryViewDep,
    ProductModelsSellingPriceDep,
)
from webstudio_backend.api.response_helpers import build_envelope, build_page_meta
from webstudio_backend.api.schemas.catalogue_deletion import ProductModelDeletePreviewResponse
from webstudio_backend.api.schemas.product_model import (
    AccessorySpecLookupRequest,
    AccessorySpecLookupResponse,
    CreateProductModelRequest,
    ProductModelImageResolveResponse,
    ProductModelResponse,
    ProductModelSpecLookupRequest,
    ProductModelSpecLookupResponse,
    UpdateLivePriceRequest,
    UpdateProductModelRequest,
    UpdateSellingPriceRequest,
)
from webstudio_backend.api.schemas.responses import ResponseMeta
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.enums import (
    ProductCategory,
    ProductModelStatus,
    UserRole,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateModelNumberError
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.ai.enrichment_service import ProductEnrichmentService
from webstudio_backend.services.ai.types import AIProviderError
from webstudio_backend.services.asus_live_price_jobs import (
    get_asus_bulk_run_status,
    retry_failed_asus_price_refreshes,
    schedule_all_asus_price_refreshes,
    schedule_asus_price_refresh,
)
from webstudio_backend.services.product_image_jobs import (
    is_product_image_job_running,
    schedule_product_image_resolve,
)
from webstudio_backend.services.product_image_service import resolve_product_image
from webstudio_backend.services.product_model_deletion_service import ProductModelDeletionService

router = APIRouter(prefix="/api/v1/product-models", tags=["product-models"])


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return build_envelope(request, data, meta)


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


async def _resolve_and_store_product_image(
    pm: ProductModel,
    *,
    brand_name: str | None,
    db_session: AsyncSession,
    repo: ProductModelRepository,
    actor: AuditActor,
    app_settings,
    candidate_url: str | None = None,
) -> ProductModel:
    if pm.product_image_url:
        return pm

    image_url = await resolve_product_image(
        model_number=pm.model_number,
        brand_name=brand_name,
        model_name=pm.model_name,
        candidate_url=candidate_url,
        model_id=str(pm.id),
        persist_local=True,
    )
    if not image_url:
        return pm

    updated = await repo.update(
        pm,
        product_image_url=image_url,
        actor=actor,
    )
    return updated


def _product_model_list_filters(
    *,
    brand_id: int | None,
    category: ProductCategory | None,
    active: bool | None,
    archived: bool | None,
    search: str | None,
) -> list:
    clauses: list = []
    if brand_id is not None:
        clauses.append(ProductModel.brand_id == brand_id)
    if category is not None:
        clauses.append(ProductModel.category == category)
    if active is not None:
        if active:
            clauses.append(ProductModel.status == ProductModelStatus.ACTIVE)
        else:
            clauses.append(ProductModel.status != ProductModelStatus.ACTIVE)
    if archived is not None:
        if archived:
            clauses.append(ProductModel.status == ProductModelStatus.ARCHIVED)
        else:
            clauses.append(ProductModel.status != ProductModelStatus.ARCHIVED)
    if search and search.strip():
        term = f"{search.strip()}%"
        clauses.append(
            (ProductModel.model_number.ilike(term))
            | (ProductModel.model_name.ilike(term))
            | (ProductModel.part_number.ilike(term)),
        )
    return clauses


@router.get("")
async def list_product_models(
    request: Request,
    current: ProductModelsOrInventoryViewDep,
    brand_id: int | None = None,
    category: ProductCategory | None = None,
    active: bool | None = None,
    archived: bool | None = None,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=128),
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    filters = _product_model_list_filters(
        brand_id=brand_id,
        category=category,
        active=active,
        archived=archived,
        search=search,
    )
    statement = (
        select(ProductModel)
        .where(*filters)
        .order_by(ProductModel.model_name, ProductModel.model_number)
    )

    brand_repo = BrandRepository(db_session)

    if page is not None:
        page_result = await paginate(
            db_session, statement, PageParams(page=page, page_size=page_size)
        )
        brand_names: dict[int, str] = {}
        for pm in page_result.items:
            if pm.brand_id not in brand_names:
                brand = await brand_repo.get_by_id(pm.brand_id)
                brand_names[pm.brand_id] = brand.name if brand else ""
        data = [
            _model_payload(pm, brand_name=brand_names.get(pm.brand_id), current=current)
            for pm in page_result.items
        ]
        return _envelope(
            request,
            data,
            build_page_meta(
                page_result.page,
                page_result.page_size,
                page_result.total_items,
                page_result.total_pages,
            ),
        )

    result = await db_session.execute(
        select(ProductModel, Brand.name)
        .outerjoin(Brand, ProductModel.brand_id == Brand.id)
        .where(*filters)
        .order_by(ProductModel.model_name, ProductModel.model_number),
    )
    product_models = result.all()
    data = [_model_payload(row[0], brand_name=row[1], current=current) for row in product_models]
    return _envelope(request, data)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product_model(
    request: Request,
    body: CreateProductModelRequest,
    current: ProductModelsCreateDep,
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
            "NOT_FOUND",
            f"Brand '{brand.name}' is not available",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Commit the model immediately. Do not block create on image discovery
    # (can take 15–20s+); clients call POST .../resolve-image separately.
    # Blocking image work previously caused API client timeouts, retries, and
    # orphan models with zero stock when the retry hit the unique constraint.
    repo = ProductModelRepository(db_session)
    try:
        pm = await repo.create(
            brand_id=body.brand_id,
            category=body.category,
            accessory_kind=body.accessory_kind,
            part_number=body.part_number,
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
        # Image discovery is slow and optional — run in background so create stays fast.
        if not pm.product_image_url:
            schedule_product_image_resolve(pm.id)
        # ASUS-only live price lookup — no-ops for every other brand.
        schedule_asus_price_refresh(pm.id)
        return _envelope(request, _model_payload(pm, brand_name=brand.name, current=current))
    except DuplicateModelNumberError as err:
        await db_session.rollback()
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err
    except IntegrityError as err:
        await db_session.rollback()
        raise AppError(
            "VALIDATION_ERROR",
            str(DuplicateModelNumberError(body.brand_id, body.model_number)),
            status_code=status.HTTP_409_CONFLICT,
        ) from err


@router.get("/refresh-live-prices/status")
async def get_asus_live_price_refresh_status(
    request: Request,
    current: ProductModelsSellingPriceDep,
) -> dict:
    """Real progress for the most recent bulk "Update prices" run — lets any
    client (desktop or mobile) poll for live/resumable progress regardless
    of which page it's on, whether it triggered the run itself, or whether
    the app was reopened mid-run or after it finished. Declared ahead of the
    `/{model_id}` route below so this static path isn't swallowed as a
    model_id."""
    _ = current
    return _envelope(request, get_asus_bulk_run_status())


@router.get("/{model_id}")
async def get_product_model(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsOrInventoryViewDep,
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
    current: ProductModelsEditDep,
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
                "NOT_FOUND",
                f"Brand '{brand.name}' is not available",
                status_code=status.HTTP_404_NOT_FOUND,
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
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err


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


@router.patch("/{model_id}/live-price")
async def update_product_model_live_price(
    request: Request,
    model_id: uuid.UUID,
    body: UpdateLivePriceRequest,
    current: ProductModelsSellingPriceDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    """Manually set (or clear) the ASUS live price — same trust tier as
    editing the selling price. Lets a user fix a wrong/missing price by hand;
    the next successful automatic refresh (scheduled or "Update prices")
    silently overwrites it again, so a manual correction never sticks around
    once the real price is fetchable."""
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    updated = await repo.set_manual_live_price(pm, price=body.live_price)
    await db_session.commit()
    brand_repo = BrandRepository(db_session)
    brand = await brand_repo.get_by_id(updated.brand_id)
    brand_name = brand.name if brand else None
    return _envelope(request, _model_payload(updated, brand_name=brand_name, current=current))


@router.post("/{model_id}/refresh-live-price")
async def refresh_product_model_live_price(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsLivePriceRefreshDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    """ASUS-only, admin-tier only (spends real Gemini API quota). Schedules
    an immediate background refresh — no-ops (but still returns success) for
    any other brand, matching the scheduler's own no-op behavior rather than
    surfacing it as an error."""
    _ = current
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    scheduled = schedule_asus_price_refresh(model_id, force=True)
    return _envelope(request, {"scheduled": scheduled})


@router.post("/refresh-live-prices")
async def refresh_all_asus_live_prices(
    request: Request,
    current: ProductModelsLivePriceRefreshDep,
) -> dict:
    """The "Update prices" button — refreshes every active ASUS model now.
    Admin-tier only: a single click can spend real Gemini API quota across
    the whole catalogue."""
    _ = current
    scheduled = await schedule_all_asus_price_refreshes()
    return _envelope(request, {"scheduled": scheduled})


@router.post("/refresh-live-prices/retry-failed")
async def retry_failed_asus_live_prices(
    request: Request,
    current: ProductModelsLivePriceRefreshDep,
) -> dict:
    """The "Retry failed" button — re-runs only the models that didn't come
    back "ok" in the most recent bulk run. Admin-tier only, same as the bulk
    trigger it complements."""
    _ = current
    scheduled = await retry_failed_asus_price_refreshes()
    return _envelope(request, {"scheduled": scheduled})


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_model(
    model_id: uuid.UUID,
    current: ProductModelsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
) -> None:
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        await ProductModelDeletionService(db_session).delete_product_model(
            pm, actor=_actor(current)
        )
        await db_session.commit()
    except Exception as exc:
        raise_catalogue_deletion_error(exc)


@router.get("/{model_id}/delete-preview")
async def product_model_delete_preview(
    request: Request,
    model_id: uuid.UUID,
    current: ProductModelsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = ProductModelRepository(db_session)
    pm = await repo.get_by_id(model_id)
    if not pm:
        raise AppError(
            "NOT_FOUND",
            f"Product model with ID {model_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    preview = await ProductModelDeletionService(db_session).preview(pm)
    return _envelope(
        request, ProductModelDeletePreviewResponse.model_validate(preview).model_dump()
    )


@router.post("/spec-lookup")
async def lookup_product_model_spec(
    request: Request,
    body: ProductModelSpecLookupRequest,
    current: ProductModelsCreateDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    del current
    service = ProductEnrichmentService(db_session, app_settings)
    try:
        result = await service.lookup_laptop_spec(
            body.model_number,
            model_name=body.model_name,
            brand_name=body.brand_name,
            force_refresh=body.force_refresh,
        )
    except AIProviderError as exc:
        status_code = status.HTTP_404_NOT_FOUND
        if exc.code == "RATE_LIMITED":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif exc.code in {"SERVICE_UNAVAILABLE", "NOT_CONFIGURED"}:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code in {"API_ERROR", "TIMEOUT", "QUOTA_EXCEEDED"}:
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
        description=result.get("description"),
        notes=result.get("notes"),
        source=result.get("source", "gemini"),
        provider=result.get("provider"),
        confidence_score=result.get("confidence_score"),
        cached=bool(result.get("cached")),
    )
    return _envelope(request, response.model_dump())


@router.post("/accessory-spec-lookup")
async def lookup_accessory_spec(
    request: Request,
    body: AccessorySpecLookupRequest,
    current: ProductModelsCreateDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    del current
    service = ProductEnrichmentService(db_session, app_settings)
    try:
        result = await service.lookup_accessory_spec(
            body.identifier,
            identifier_type=body.identifier_type,
            brand_name=body.brand_name,
            accessory_kind=body.accessory_kind,
            model_name=body.model_name,
            force_refresh=body.force_refresh,
        )
    except AIProviderError as exc:
        status_code = status.HTTP_404_NOT_FOUND
        if exc.code == "RATE_LIMITED":
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif exc.code in {"SERVICE_UNAVAILABLE", "NOT_CONFIGURED"}:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.code in {"API_ERROR", "TIMEOUT", "QUOTA_EXCEEDED"}:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise AppError(exc.code, exc.message, status_code=status_code) from exc

    response = AccessorySpecLookupResponse(
        model_name=result["model_name"],
        model_number=result.get("model_number"),
        part_number=result.get("part_number"),
        accessory_kind=result.get("accessory_kind"),
        color_options=result.get("color_options"),
        product_image_url=result.get("product_image_url"),
        description=result.get("description"),
        notes=result.get("notes"),
        source=result.get("source", "gemini"),
        provider=result.get("provider"),
        confidence_score=result.get("confidence_score"),
        cached=bool(result.get("cached")),
    )
    return _envelope(request, response.model_dump())


@router.post("/{model_id}/resolve-image")
async def resolve_product_model_image(
    request: Request,
    model_id: uuid.UUID,
    current_user: ProductModelsEditDep,
    db_session: AsyncSession = DbSessionDep,
    wait: bool = Query(
        default=False,
        description="If true, block until discovery finishes. Default is background (pending).",
    ),
    app_settings=AppSettingsDep,
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

    if pm.product_image_url:
        response = ProductModelImageResolveResponse(
            product_image_url=pm.product_image_url,
            source="database",
        )
        return _envelope(request, response.model_dump())

    if not wait:
        scheduled = schedule_product_image_resolve(model_id, force=True)
        response = ProductModelImageResolveResponse(
            product_image_url=None,
            source=(
                "pending" if scheduled or is_product_image_job_running(model_id) else "unresolved"
            ),
        )
        return _envelope(request, response.model_dump())

    updated = await _resolve_and_store_product_image(
        pm,
        brand_name=brand_name,
        db_session=db_session,
        repo=repo,
        actor=_actor(current_user),
        app_settings=app_settings,
    )
    if updated.product_image_url and not pm.product_image_url:
        await db_session.commit()

    response = ProductModelImageResolveResponse(
        product_image_url=updated.product_image_url,
        source="resolved" if updated.product_image_url else "unresolved",
    )
    return _envelope(request, response.model_dump())
