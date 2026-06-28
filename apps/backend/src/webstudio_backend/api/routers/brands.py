"""Brand API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from webstudio_backend.api.dependencies.auth import AuthenticatedUser, require_permission
from webstudio_backend.api.schemas.brand import BrandResponse, CreateBrandRequest, UpdateBrandRequest
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])

BrandsReadDep = Annotated[AuthenticatedUser, Depends(require_permission("brands:read"))]
BrandsWriteDep = Annotated[AuthenticatedUser, Depends(require_permission("brands:write"))]


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


@router.get("")
async def list_brands(
    request: Request,
    current: BrandsReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    statement = select(Brand)
    result = await db_session.execute(statement)
    brands = result.scalars().all()
    # Sort brands by display_order, then by name
    sorted_brands = sorted(brands, key=lambda b: (b.display_order, b.name.lower()))
    return _envelope(
        request,
        [BrandResponse.from_model(b).model_dump() for b in sorted_brands],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_brand(
    request: Request,
    body: CreateBrandRequest,
    current: BrandsWriteDep,
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
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, BrandResponse.from_model(brand).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


@router.get("/{brand_id}")
async def get_brand(
    request: Request,
    brand_id: int,
    current: BrandsReadDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError("NOT_FOUND", f"Brand with ID {brand_id} not found", status_code=status.HTTP_404_NOT_FOUND)
    return _envelope(request, BrandResponse.from_model(brand).model_dump())


@router.patch("/{brand_id}")
async def update_brand(
    request: Request,
    brand_id: int,
    body: UpdateBrandRequest,
    current: BrandsWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError("NOT_FOUND", f"Brand with ID {brand_id} not found", status_code=status.HTTP_404_NOT_FOUND)

    try:
        updated = await repo.update(
            brand,
            name=body.name,
            short_name=body.short_name,
            logo_filename=body.logo_filename,
            display_order=body.display_order,
            is_active=body.is_active,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, BrandResponse.from_model(updated).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


@router.post("/{brand_id}/archive")
async def archive_brand(
    request: Request,
    brand_id: int,
    current: BrandsWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError("NOT_FOUND", f"Brand with ID {brand_id} not found", status_code=status.HTTP_404_NOT_FOUND)

    updated = await repo.update(
        brand,
        is_active=False,
        actor=_actor(current),
    )
    await db_session.commit()
    return _envelope(request, BrandResponse.from_model(updated).model_dump())


@router.post("/{brand_id}/restore")
async def restore_brand(
    request: Request,
    brand_id: int,
    current: BrandsWriteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = BrandRepository(db_session)
    brand = await repo.get_by_id(brand_id)
    if not brand:
        raise AppError("NOT_FOUND", f"Brand with ID {brand_id} not found", status_code=status.HTTP_404_NOT_FOUND)

    updated = await repo.update(
        brand,
        is_active=True,
        actor=_actor(current),
    )
    await db_session.commit()
    return _envelope(request, BrandResponse.from_model(updated).model_dump())
