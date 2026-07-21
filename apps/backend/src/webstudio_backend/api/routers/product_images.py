"""Authenticated product image proxy and upload."""

from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

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
from webstudio_backend.services.product_image_jobs import schedule_product_image_resolve
from webstudio_backend.services.product_image_service import (
    USER_AGENT,
    image_bytes_too_small,
    is_safe_public_https_url,
    validate_image_url,
    validate_product_image_upload,
)
from webstudio_backend.services.web_image_scraper import (
    find_managed_product_image_path,
    resolve_managed_assets_dir,
)

router = APIRouter(prefix="/api/v1/product-images", tags=["product-images"])

_MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# Windows Python installs often omit webp/avif from the system MIME map.
_MANAGED_IMAGE_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
}


def _sniff_image_content_type(payload: bytes) -> str | None:
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"GIF87a") or payload.startswith(b"GIF89a"):
        return "image/gif"
    if len(payload) >= 12 and payload[0:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    return None


def _managed_image_content_type(filename: str, payload: bytes | None = None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in _MANAGED_IMAGE_CONTENT_TYPES:
        return _MANAGED_IMAGE_CONTENT_TYPES[suffix]
    if payload:
        sniffed = _sniff_image_content_type(payload)
        if sniffed:
            return sniffed
    guessed = mimetypes.guess_type(filename)[0]
    return guessed or "application/octet-stream"


# Real product photos exceed this; only files below it are decode-checked.
_JUNK_IMAGE_MAX_BYTES = 10 * 1024


def _is_junk_image_file(file_path: Path) -> bool:
    """Detect stored tracking pixels/icons that older scraper versions saved."""
    try:
        if file_path.stat().st_size > _JUNK_IMAGE_MAX_BYTES:
            return False
        return image_bytes_too_small(file_path.read_bytes())
    except OSError:
        return False


async def _heal_missing_product_image(url: str, db_session: AsyncSession) -> None:
    """Managed product-image files are named `{model_id}.{ext}`. When the file
    is gone (e.g. storage location changed between versions), clear the dead
    URL and re-run background discovery so the image repairs itself."""
    relative = url.removeprefix("/assets/").lstrip("/").replace("\\", "/")
    if not relative.startswith("product-images/"):
        return
    stem = relative.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    try:
        model_id = uuid.UUID(stem)
    except ValueError:
        return
    repo = ProductModelRepository(db_session)
    model = await repo.get_by_id(model_id)
    if model is None or model.product_image_url != url:
        return
    model.product_image_url = None
    await db_session.commit()
    schedule_product_image_resolve(model_id, force=True)


async def _serve_managed_asset(url: str, db_session: AsyncSession) -> Response:
    if not url.startswith("/assets/"):
        raise AppError(
            "VALIDATION_ERROR",
            "Invalid managed asset path.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    relative = url.removeprefix("/assets/").lstrip("/").replace("\\", "/")
    file_path = find_managed_product_image_path(relative)
    while file_path is not None and _is_junk_image_file(file_path):
        try:
            file_path.unlink()
        except OSError:
            file_path = None
            break
        # The same junk file may exist in more than one storage location.
        file_path = find_managed_product_image_path(relative)
    if file_path is None:
        await _heal_missing_product_image(url, db_session)
        raise AppError(
            "NOT_FOUND",
            "Product image is not available.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    payload = file_path.read_bytes()
    content_type = _managed_image_content_type(file_path.name, payload)
    if not content_type.startswith("image/"):
        raise AppError(
            "NOT_FOUND",
            "URL did not resolve to an image.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # If DB pointed at .webp but disk has .jpg (or vice versa), rewrite the
    # stored URL so future clients request the file that actually exists.
    served_url = f"/assets/product-images/{file_path.name}"
    if served_url != url and relative.startswith("product-images/"):
        stem = Path(relative).stem
        try:
            model_id = uuid.UUID(stem)
        except ValueError:
            model_id = None
        if model_id is not None:
            repo = ProductModelRepository(db_session)
            model = await repo.get_by_id(model_id)
            if model is not None and model.product_image_url == url:
                model.product_image_url = served_url
                await db_session.commit()

    return Response(
        content=payload,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.get("/proxy")
async def proxy_product_image(
    request: Request,
    current: ProductModelsOrInventoryViewDep,
    url: str = Query(..., min_length=4, max_length=512),
    db_session: AsyncSession = DbSessionDep,
) -> Response:
    del request, current
    if url.startswith("/assets/"):
        return await _serve_managed_asset(url, db_session)

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

    assets_root = resolve_managed_assets_dir()
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
