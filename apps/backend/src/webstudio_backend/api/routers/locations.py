"""Location API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.catalogue_errors import raise_catalogue_deletion_error
from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    LocationsCreateDep,
    LocationsDeleteDep,
    LocationsEditDep,
    LocationsViewDep,
)
from webstudio_backend.api.response_helpers import build_envelope, build_page_meta
from webstudio_backend.api.schemas.catalogue_deletion import (
    DeleteLocationRequest,
    LocationDeletePreviewResponse,
)
from webstudio_backend.api.schemas.location import (
    CreateLocationRequest,
    LocationResponse,
    UpdateLocationRequest,
)
from webstudio_backend.api.schemas.responses import ResponseMeta
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.database.repositories.pagination import PageParams, paginate
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.services.location_deletion_service import LocationDeletionService

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


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
async def list_locations(
    request: Request,
    current: LocationsViewDep,
    db_session: AsyncSession = DbSessionDep,
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    search: str | None = Query(default=None, max_length=128),
) -> dict:
    del current
    statement = select(Location).order_by(Location.sort_order.nulls_last(), Location.name)
    if search and search.strip():
        statement = statement.where(Location.name.ilike(f"{search.strip()}%"))

    if page is not None:
        page_result = await paginate(
            db_session, statement, PageParams(page=page, page_size=page_size)
        )
        data = [LocationResponse.from_model(item).model_dump() for item in page_result.items]
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
    locations = result.scalars().all()
    return _envelope(
        request,
        [LocationResponse.from_model(item).model_dump() for item in locations],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_location(
    request: Request,
    body: CreateLocationRequest,
    current: LocationsCreateDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = LocationRepository(db_session)
    try:
        location = await repo.create(
            name=body.name,
            location_type=body.location_type,
            is_active=body.is_active,
            sort_order=body.sort_order,
            branch_id=body.branch_id,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, LocationResponse.from_model(location).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err


@router.get("/{location_id}")
async def get_location(
    request: Request,
    location_id: int,
    current: LocationsViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = LocationRepository(db_session)
    location = await repo.get_by_id(location_id)
    if not location:
        raise AppError(
            "NOT_FOUND",
            f"Location with ID {location_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return _envelope(request, LocationResponse.from_model(location).model_dump())


@router.get("/{location_id}/delete-preview")
async def location_delete_preview(
    request: Request,
    location_id: int,
    current: LocationsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    repo = LocationRepository(db_session)
    location = await repo.get_by_id(location_id)
    if not location:
        raise AppError(
            "NOT_FOUND",
            f"Location with ID {location_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    preview = await LocationDeletionService(db_session).preview(location)
    return _envelope(request, LocationDeletePreviewResponse.model_validate(preview).model_dump())


@router.patch("/{location_id}")
async def update_location(
    request: Request,
    location_id: int,
    body: UpdateLocationRequest,
    current: LocationsEditDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    repo = LocationRepository(db_session)
    location = await repo.get_by_id(location_id)
    if not location:
        raise AppError(
            "NOT_FOUND",
            f"Location with ID {location_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        updated = await repo.update(
            location,
            name=body.name,
            location_type=body.location_type,
            is_active=body.is_active,
            sort_order=body.sort_order,
            branch_id=body.branch_id,
            actor=_actor(current),
        )
        await db_session.commit()
        return _envelope(request, LocationResponse.from_model(updated).model_dump())
    except DuplicateNameError as err:
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT) from err


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_location(
    location_id: int,
    current: LocationsDeleteDep,
    db_session: AsyncSession = DbSessionDep,
    body: DeleteLocationRequest = Body(default_factory=DeleteLocationRequest),
) -> None:
    repo = LocationRepository(db_session)
    location = await repo.get_by_id(location_id)
    if not location:
        raise AppError(
            "NOT_FOUND",
            f"Location with ID {location_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        await LocationDeletionService(db_session).delete_location(
            location,
            transfer_to_location_id=body.transfer_to_location_id,
            actor=_actor(current),
        )
        await db_session.commit()
    except Exception as exc:
        raise_catalogue_deletion_error(exc)
