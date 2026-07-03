"""Authenticated product image proxy and upload."""

from __future__ import annotations

import mimetypes
import uuid

import httpx
from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.dependencies.auth import (
    ProductModelsEditDep,
    ProductModelsOrInventoryViewDep,
)
from webstudio_backend.api.response_helpers import build_envelope
from webstudio_backend.core.dependencies import DbSessionDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.product_image_service import (
    USER_AGENT,
    is_safe_public_https_url,
    validate_image_url,
    validate_product_image_upload,
)
from webstudio_backend.services.web_image_scraper import find_public_assets_dir

router = APIRouter(prefix="/api/v1/product-images", tags=["product-images"])

_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _serve_managed_asset(url: str) -> Response:
    if not url.startswith("/assets/"):
        raise AppError(
            "VALIDATION_ERROR",
            "Invalid managed asset path.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    assets_root = find_public_assets_dir()
    if assets_root is None:
        raise AppError(
            "NOT_FOUND",
            "Managed asset storage is not available.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    relative = url.removeprefix("/assets/").lstrip("/")
    file_path = (assets_root / relative).resolve()
    root = assets_root.resolve()
    if not str(file_path).startswith(str(root)) or not file_path.is_file():
        raise AppError(
            "NOT_FOUND",
            "Product image is not available.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise AppError(
            "NOT_FOUND",
            "URL did not resolve to an image.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        content=file_path.read_bytes(),
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/proxy")
async def proxy_product_image(
    request: Request,
    current: ProductModelsOrInventoryViewDep,
    url: str = Query(..., min_length=4, max_length=512),
) -> Response:
    del request, current
    if url.startswith("/assets/"):
        return _serve_managed_asset(url)

    if not is_safe_public_https_url(url):
        raise AppError(
            "VALIDATION_ERROR",
            "Only public HTTPS image URLs are allowed.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if not await validate_image_url(url):
        raise AppError(
            "NOT_FOUND",
            "Product image is not available at the provided URL.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            upstream = await client.get(url)
    except httpx.HTTPError as exc:
        raise AppError(
            "API_ERROR",
            "Could not fetch product image.",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc

    if upstream.status_code >= 400:
        raise AppError(
            "NOT_FOUND",
            "Product image is not available.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    content_type = upstream.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    if not content_type.startswith("image/"):
        raise AppError(
            "NOT_FOUND",
            "URL did not return an image.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        content=upstream.content,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/upload")
async def upload_product_image(
    request: Request,
    current: ProductModelsEditDep,
    db_session: AsyncSession = DbSessionDep,
    product_model_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
) -> dict:
    repo = ProductModelRepository(db_session)
    model = await repo.get_by_id(product_model_id)
    if model is None:
        raise AppError(
            "NOT_FOUND", "Product model not found.", status_code=status.HTTP_404_NOT_FOUND
        )

    payload = await file.read()
    if len(payload) > _MAX_UPLOAD_BYTES:
        raise AppError(
            "VALIDATION_ERROR",
            "Image must be 5 MB or smaller.",
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

    assets_root = find_public_assets_dir()
    if assets_root is None:
        raise AppError(
            "SERVICE_UNAVAILABLE",
            "Managed asset storage is not available on this server.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    folder = assets_root / "product-images"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{product_model_id}.{image_format}"
    (folder / filename).write_bytes(payload)
    image_url = f"/assets/product-images/{filename}"

    updated = await repo.update(
        model,
        product_image_url=image_url,
        actor=AuditActor(
            user_id=current.user.id,
            display_name=current.user.display_name or current.user.username,
            role=current.user.role.value,
        ),
    )
    await db_session.commit()
    return build_envelope(
        request,
        {
            "product_model_id": str(updated.id),
            "product_image_url": updated.product_image_url,
            "source": "upload",
        },
    )
