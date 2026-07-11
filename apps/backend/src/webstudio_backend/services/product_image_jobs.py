"""Background product-image discovery jobs (non-blocking for API requests)."""

from __future__ import annotations

import asyncio
import uuid

from loguru import logger

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.session import get_session_factory
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.product_image_service import resolve_product_image

_inflight: dict[str, asyncio.Task[None]] = {}


def is_product_image_job_running(model_id: uuid.UUID | str) -> bool:
    key = str(model_id)
    task = _inflight.get(key)
    return task is not None and not task.done()


def schedule_product_image_resolve(model_id: uuid.UUID | str) -> bool:
    """Start background image discovery if not already running. Returns True if scheduled."""
    key = str(model_id)
    existing = _inflight.get(key)
    if existing is not None and not existing.done():
        return False

    task = asyncio.create_task(
        _run_product_image_resolve(uuid.UUID(str(model_id))), name=f"product-image:{key}"
    )
    _inflight[key] = task

    def _cleanup(done: asyncio.Task[None]) -> None:
        current = _inflight.get(key)
        if current is done:
            _inflight.pop(key, None)

    task.add_done_callback(_cleanup)
    return True


async def _run_product_image_resolve(model_id: uuid.UUID) -> None:
    try:
        factory = get_session_factory()
        async with factory() as session:
            repo = ProductModelRepository(session)
            pm = await repo.get_by_id(model_id)
            if pm is None:
                logger.info("Background image resolve skipped; model {} not found", model_id)
                return
            if pm.product_image_url:
                logger.debug(
                    "Background image resolve skipped; model {} already has image", model_id
                )
                return

            brand = await BrandRepository(session).get_by_id(pm.brand_id)
            brand_name = brand.name if brand else None
            image_url = await resolve_product_image(
                model_number=pm.model_number,
                brand_name=brand_name,
                model_name=pm.model_name,
                model_id=str(pm.id),
                persist_local=True,
            )
            if not image_url:
                logger.info(
                    "Background image resolve found nothing for {} ({})",
                    pm.model_number,
                    model_id,
                )
                return

            await repo.update(
                pm,
                product_image_url=image_url,
                actor=AuditActor.system(display_name="Image Resolver", role="system"),
            )
            await session.commit()
            logger.info(
                "Background image resolve stored image for {} ({})",
                pm.model_number,
                model_id,
            )
    except Exception:
        logger.exception("Background image resolve failed for model {}", model_id)
