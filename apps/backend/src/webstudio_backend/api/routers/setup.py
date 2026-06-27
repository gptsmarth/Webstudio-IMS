"""Setup API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.responses import Envelope, utc_now_iso
from webstudio_backend.api.schemas.user import (
    SetupConfirmRecoveryKeyResponse,
    SetupInitializeRequest,
    SetupInitializeResponse,
    SetupStatusResponse,
    UserSummary,
)
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.request_context import get_correlation_id, get_request_id
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateUsernameError,
    SetupPendingRecoveryConfirmationError,
    SystemAlreadyInitializedError,
)
from webstudio_backend.services.setup_service import SetupService

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


def _envelope(request: Request, data: object) -> dict:
    return Envelope(
        data=data,
        request_id=get_request_id(request),
        correlation_id=get_correlation_id(request),
        timestamp=utc_now_iso(),
    ).model_dump()


@router.get("/status")
async def setup_status(request: Request, db_session: AsyncSession = DbSessionDep) -> dict:
    status_data = await SetupService(db_session).get_status()
    return _envelope(request, SetupStatusResponse(**status_data).model_dump())


@router.post("/initialize", status_code=status.HTTP_201_CREATED)
async def setup_initialize(
    request: Request,
    body: SetupInitializeRequest,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = SetupService(db_session)
    try:
        result = await service.initialize(
            company_name=body.company_name,
            main_admin_name=body.main_admin_name,
            username=body.username,
            password=body.password,
            confirm_password=body.confirm_password,
        )
    except SystemAlreadyInitializedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except SetupPendingRecoveryConfirmationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DuplicateUsernameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    response = SetupInitializeResponse(
        company_name=result.company_name,
        main_admin=UserSummary.from_model(result.user),
        recovery_key=result.recovery_key,
    )
    return _envelope(request, response.model_dump())


@router.post("/confirm-recovery-key")
async def confirm_recovery_key(
    request: Request,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    service = SetupService(db_session)
    try:
        await service.confirm_recovery_key()
    except SystemAlreadyInitializedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _envelope(request, SetupConfirmRecoveryKeyResponse().model_dump())
