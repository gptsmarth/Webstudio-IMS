"""Location API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    LocationsArchiveDep,
    LocationsCreateDep,
    LocationsEditDep,
    LocationsViewDep,
)
from webstudio_backend.api.schemas.location import (
    CreateLocationRequest,
    LocationResponse,
    UpdateLocationRequest,
)
from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.models.location import Location
from webstudio_backend.infrastructure.repositories.exceptions import DuplicateNameError
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


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
async def list_locations(
    request: Request,
    current: LocationsViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    del current
    statement = select(Location)
    result = await db_session.execute(statement)
    locations = result.scalars().all()
    # Sort locations by sort_order (put None last), then by name
    sorted_locations = sorted(
        locations,
        key=lambda l: (l.sort_order if l.sort_order is not None else float("inf"), l.name.lower()),
    )
    return _envelope(
        request,
        [LocationResponse.from_model(l).model_dump() for l in sorted_locations],
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
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


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
        raise AppError("VALIDATION_ERROR", str(err), status_code=status.HTTP_409_CONFLICT)


@router.post("/{location_id}/archive")
async def archive_location(
    request: Request,
    location_id: int,
    current: LocationsArchiveDep,
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

    updated = await repo.update(
        location,
        is_active=False,
        actor=_actor(current),
    )
    await db_session.commit()
    return _envelope(request, LocationResponse.from_model(updated).model_dump())


@router.post("/{location_id}/restore")
async def restore_location(
    request: Request,
    location_id: int,
    current: LocationsArchiveDep,
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

    updated = await repo.update(
        location,
        is_active=True,
        actor=_actor(current),
    )
    await db_session.commit()
    return _envelope(request, LocationResponse.from_model(updated).model_dump())
