"""Authenticated product image proxy."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Query, Request, status
from fastapi.responses import Response

from webstudio_backend.api.dependencies.auth import ProductModelsViewDep
from webstudio_backend.core.exceptions import AppError
from webstudio_backend.services.product_image_service import (
    USER_AGENT,
    is_safe_public_https_url,
    validate_image_url,
)

router = APIRouter(prefix="/api/v1/product-images", tags=["product-images"])


@router.get("/proxy")
async def proxy_product_image(
    request: Request,
    current: ProductModelsViewDep,
    url: str = Query(..., min_length=10, max_length=512),
) -> Response:
    del request, current
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
