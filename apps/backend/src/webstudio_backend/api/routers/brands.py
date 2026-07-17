"""Brand API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.catalogue_errors import raise_catalogue_deletion_error
from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    BrandsCreateDep,
    BrandsDeleteDep,
    BrandsEditDep,
    BrandsOrInventoryViewDep,
    BrandsViewDep,
)
from webstudio_backend.api.response_helpers import build_envelope, build_page_meta
from webstudio_backend.api.schemas.brand import (
    BrandResponse,
    CreateBrandRequest,
    UpdateBrandRequest,
)
from webstudio_backend.api.schemas.catalogue_deletion import BrandDeletePreviewResponse
from webstudio_backend.api.schemas.responses import ResponseMeta
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.services.brand_deletion_service import BrandDeletionService
from webstudio_backend.services.product_image_service import validate_product_image_upload
from webstudio_backend.services.web_image_scraper import resolve_managed_assets_dir

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])

# Brand logos are small; keep the same ceiling as product image uploads.
_MAX_LOGO_BYTES = 5 * 1024 * 1024


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return build_envelope(request, data, meta)


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


@router.get("")
async def list_brands(
    request: Request,
    current: BrandsOrInventoryViewDep,
    db_session: AsyncSession = DbSessionDep,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=128),
) -> dict:
    del current
    statement = select(Brand).order_by(Brand.display_order, Brand.name)
    if search and search.strip():
        statement = statement.where(Brand.name.ilike(f"{search.strip()}%"))

    if page is not None:
        page_result = await paginate(
            db_session, statement, PageParams(page=page, page_size=page_size)
        )
        data = [BrandResponse.from_model(b).model_dump() for b in page_result.items]
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

    result = await db_session.execute(statement)
    brands = result.scalars().all()
    return _envelope(
        request,
        [BrandResponse.from_model(b).model_dump() for b in brands],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brand(
    request: Request,
    body: CreateBrandRequest,
    current: BrandsCreateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = BrandRepository(db_session)
    try:
        brand = await repo.create(
            name=body.name,
            short_name=body.short_name,
            logo_filename=body.logo_filename,
            display_order=body.display_order,
            is_active=body.is_active,
            allow_duplicate_serials=body.allow_duplicate_serials,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, BrandResponse.from_model(brand).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err


@router.get("/{brand_id}")
async def get_brand(
    request: Request,
    brand_id: int,
    current: BrandsViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError(
            "NOT_FOUND",
            f"Brand with ID {brand_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _envelope(request, BrandResponse.from_model(brand).model_dump())


@router.get("/{brand_id}/delete-preview")
async def brand_delete_preview(
    request: Request,
    brand_id: int,
    current: BrandsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError(
            "NOT_FOUND",
            f"Brand with ID {brand_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    preview = await BrandDeletionService(db_session).preview(brand)
    return _envelope(request, BrandDeletePreviewResponse.model_validate(preview).model_dump())


@router.patch("/{brand_id}")
async def update_brand(
    request: Request,
    brand_id: int,
    body: UpdateBrandRequest,
    current: BrandsEditDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError(
            "NOT_FOUND",
            f"Brand with ID {brand_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        updated = await repo.update(
            brand,
            name=body.name,
            short_name=body.short_name,
            logo_filename=body.logo_filename,
            display_order=body.display_order,
            is_active=body.is_active,
            allow_duplicate_serials=body.allow_duplicate_serials,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, BrandResponse.from_model(updated).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err


@router.post("/{brand_id}/logo")
async def upload_brand_logo(
    request: Request,
    brand_id: int,
    current: BrandsEditDep,
    db_session: AsyncSession = DbSessionDep,
    file: UploadFile = File(...),
) -> dict:
    """Upload a custom brand logo (PNG/JPG/WebP).

    Reuses the exact same safe image validation as product image uploads
    (extension + MIME + magic-byte + decodability checks) and stores the file
    as a server-managed asset. ``logo_filename`` is set to the ``/assets/...``
    path, which clients render through the existing authenticated image proxy.
    """
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError(
            "NOT_FOUND",
            f"Brand with ID {brand_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    payload = await file.read()
    if len(payload) > _MAX_LOGO_BYTES:
        raise AppError(
            "VALIDATION_ERROR",
            "Logo must be 5 MB or smaller.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        image_format = validate_product_image_upload(
            filename=file.filename,
            content_type=file.content_type,
            payload=payload,
        )
    except ValueError as exc:
        raise AppError(
            "VALIDATION_ERROR",
            str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        ) from exc

    assets_root = resolve_managed_assets_dir()
    if assets_root is None:
        raise AppError(
            "SERVICE_UNAVAILABLE",
            "Managed asset storage is not available on this server.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    folder = assets_root / "brand-logos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"brand-{brand_id}.{image_format}"
    (folder / filename).write_bytes(payload)
    logo_url = f"/assets/brand-logos/{filename}"

    updated = await repo.update(brand, logo_filename=logo_url, actor=_actor(current))
    await db_session.commit()
    return _envelope(request, BrandResponse.from_model(updated).model_dump())


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brand(
    brand_id: int,
    current: BrandsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
) -> None:
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError(
            "NOT_FOUND",
            f"Brand with ID {brand_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        await BrandDeletionService(db_session).delete_brand(brand, actor=_actor(current))
        await db_session.commit()
    except Exception as exc:
        raise_catalogue_deletion_error(exc)
