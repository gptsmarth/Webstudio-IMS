"""Laptop comparison endpoints for staff with inventory access."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import InventoryViewDep
from webstudio_backend.api.response_helpers import build_envelope, build_page_meta
from webstudio_backend.api.schemas.comparison import ExternalLaptopRequest
from webstudio_backend.core.dependencies import AppSettingsDep, DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.services.ai.types import AIProviderError
from webstudio_backend.services.laptop_comparison import (
    UNVERIFIED_MODEL,
    available_count,
    inventory_processor,
    inventory_specifications,
    list_stock_laptops,
    research_external,
    stock_laptop_filters,
)
from webstudio_backend.services.web_image_scraper import find_managed_product_image_path

router = APIRouter(prefix="/api/v1/comparison", tags=["comparison"])

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
}


@router.get("/inventory")
async def inventory_comparison(
    request: Request,
    current: InventoryViewDep,
    search: str = Query(default="", max_length=160),
    page: int = Query(default=1, ge=1, le=100000),
    page_size: int = Query(default=8, ge=1, le=30),
    db_session: AsyncSession = DbSessionDep,
) -> dict:
    models, total = await list_stock_laptops(
        db_session, search=search, page=page, page_size=page_size
    )
    meta = build_page_meta(page, page_size, total, (total + page_size - 1) // page_size)
    return build_envelope(request, [model.model_dump(mode="json") for model in models], meta)


@router.get("/inventory/{model_id}/image")
async def inventory_comparison_image(
    model_id: UUID,
    current: InventoryViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> FileResponse:
    url = await db_session.scalar(
        select(ProductModel.product_image_url).where(
            ProductModel.id == model_id, *stock_laptop_filters(available_count())
        )
    )
    if url and url.startswith("/assets/"):
        path = find_managed_product_image_path(url.removeprefix("/assets/"), settings=app_settings)
        if path is not None and (content_type := IMAGE_TYPES.get(path.suffix.lower())):
            return FileResponse(
                path, media_type=content_type, headers={"X-Content-Type-Options": "nosniff"}
            )
    raise AppError("NOT_FOUND", "Saved product image is not available.", status_code=404)


@router.post("/inventory/{model_id}/specifications")
async def refresh_inventory_specifications(
    request: Request,
    model_id: UUID,
    current: InventoryViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    result = await inventory_specifications(db_session, app_settings, model_id)
    if result is None:
        raise AppError("NOT_FOUND", "This laptop is no longer in stock.", status_code=404)
    return build_envelope(request, result.model_dump(mode="json"))


@router.post("/inventory/{model_id}/processor")
async def inventory_comparison_processor(
    request: Request,
    model_id: UUID,
    current: InventoryViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    try:
        async with asyncio.timeout(75):
            specs = await inventory_processor(db_session, app_settings, model_id)
    except TimeoutError:
        specs = []
    if specs is None:
        raise AppError("NOT_FOUND", "This laptop is no longer in stock.", status_code=404)
    return build_envelope(request, [spec.model_dump(mode="json") for spec in specs])


@router.post("/external")
async def external_comparison(
    request: Request,
    body: ExternalLaptopRequest,
    current: InventoryViewDep,
    db_session: AsyncSession = DbSessionDep,
    app_settings=AppSettingsDep,
) -> dict:
    try:
        async with asyncio.timeout(75):
            result = await research_external(db_session, app_settings, body)
    except TimeoutError as exc:
        raise AppError(
            "TIMEOUT", "The specifications search timed out. Try again.", status_code=503
        ) from exc
    except AIProviderError as exc:
        if exc.code == "NOT_FOUND":
            raise AppError("NOT_FOUND", UNVERIFIED_MODEL, status_code=404) from exc
        if exc.code == "NOT_CONFIGURED":
            raise AppError(
                "NOT_CONFIGURED",
                "External research is unavailable. Ask your administrator to check the Gemini settings.",
                status_code=503,
            ) from exc
        if exc.code == "RATE_LIMITED":
            raise AppError(
                "RATE_LIMITED",
                "Gemini is temporarily limiting searches. Try again shortly.",
                status_code=429,
            ) from exc
        raise AppError(
            "SERVICE_UNAVAILABLE",
            "Gemini could not complete the search. Try again shortly.",
            status_code=503,
        ) from exc
    return build_envelope(request, result.model_dump(mode="json"))
