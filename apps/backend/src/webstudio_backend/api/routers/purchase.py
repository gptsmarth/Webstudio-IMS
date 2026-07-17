"""Purchase Import Queue API (additive feature).

All endpoints reuse existing inventory / product-model / brand infrastructure.
No inventory is ever created without an explicit ``POST /import`` call, which
runs inside the request transaction (rollback-on-failure).
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import (
    AuthenticatedUser,
    PurchaseImportDep,
    PurchaseViewDep,
)
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.api.schemas.purchase import (
    MatchAccessoryRequest,
    MatchModelRequest,
    PurchaseImportRequest,
)
from webstudio_backend.api.schemas.responses import ResponseMeta
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.services.purchase_import_service import PurchaseImportService

router = APIRouter(prefix="/api/v1/purchase", tags=["purchase"])


def _envelope(request: Request, data: object, meta: ResponseMeta | None = None) -> dict:
    return build_envelope(request, data, meta)


def _actor(current: AuthenticatedUser) -> AuditActor:
    user = current.user
    return AuditActor(
        user_id=user.id,
        display_name=user.display_name or user.username,
        role=user.role.value,
    )


@router.get("/queue")
async def list_purchase_queue(
    request: Request,
    current: PurchaseViewDep,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    _ = current
    offset = (page - 1) * page_size
    items = await PurchaseImportService(db_session).list_queue(
        status=status, limit=page_size, offset=offset
    )
    return _envelope(request, [item.model_dump(mode="json") for item in items])


@router.get("/queue/{voucher_id}")
async def get_purchase_voucher(
    request: Request,
    voucher_id: int,
    current: PurchaseViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    _ = current
    detail = await PurchaseImportService(db_session).get_detail(voucher_id)
    return _envelope(request, detail.model_dump(mode="json"))


@router.post("/match-model")
async def match_purchase_model(
    request: Request,
    body: MatchModelRequest,
    current: PurchaseViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    _ = current
    result = await PurchaseImportService(db_session).match_model(body.brand_id, body.model_number)
    return _envelope(request, result.model_dump(mode="json"))


@router.post("/match-accessory")
async def match_purchase_accessory(
    request: Request,
    body: MatchAccessoryRequest,
    current: PurchaseViewDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    _ = current
    result = await PurchaseImportService(db_session).match_accessory(body.brand_id, body.query)
    return _envelope(request, result.model_dump(mode="json"))


@router.post("/import")
async def import_purchase_group(
    request: Request,
    body: PurchaseImportRequest,
    current: PurchaseImportDep,
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    result = await PurchaseImportService(db_session).import_group(body, actor=_actor(current))
    return _envelope(request, result.model_dump(mode="json"))
