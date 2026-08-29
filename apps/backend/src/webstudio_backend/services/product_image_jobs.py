"""Background product-image discovery jobs (non-blocking for API requests)."""

from __future__ import annotations

import asyncio
import time
import uuid

from loguru import logger

from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.database.session import get_session_factory
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.ai.prompts import default_image_search_query
from webstudio_backend.services.product_image_service import resolve_product_image
from webstudio_backend.services.scheduler_runtime_service import sleep_until_next_run
from webstudio_backend.services.web_image_scraper import _BACKGROUND_MAX_QUERIES

_inflight: dict[str, asyncio.Task[None]] = {}
# model_id -> unix timestamp when a failed attempt may be retried
_retry_after: dict[str, float] = {}
_FAILURE_COOLDOWN_SECONDS = 6 * 60 * 60  # 6 hours
_BACKFILL_BATCH_SIZE = 3
_BACKFILL_INTERVAL_SECONDS = 600  # 10 minutes
# Caps how many scraping jobs actually run their HTTP requests at once — bulk imports or
# fast sequential product creation can otherwise schedule dozens of jobs in one burst, and
# firing them all at Bing/DuckDuckGo simultaneously risks a temporary soft-block that makes
# the whole batch fail together. Jobs beyond this limit still get created immediately
# (scheduling stays non-blocking); they just queue here before doing any network I/O.
_MAX_CONCURRENT_IMAGE_JOBS = 3
_concurrency_limiter = asyncio.Semaphore(_MAX_CONCURRENT_IMAGE_JOBS)


def is_product_image_job_running(model_id: uuid.UUID | str) -> bool:
    key = str(model_id)
    task = _inflight.get(key)
    return task is not None and not task.done()


def schedule_product_image_resolve(
    model_id: uuid.UUID | str,
    *,
    force: bool = False,
) -> bool:
    """Start background image discovery if not already running. Returns True if scheduled."""
    key = str(model_id)
    existing = _inflight.get(key)
    if existing is not None and not existing.done():
        return False

    now = time.monotonic()
    retry_at = _retry_after.get(key)
    if not force and retry_at is not None and now < retry_at:
        return False
    if force:
        _retry_after.pop(key, None)

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
    key = str(model_id)
    try:
        # Acquired before opening a DB session so a queued job isn't holding a pooled
        # connection idle while it waits its turn.
        async with _concurrency_limiter:
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
                    _retry_after.pop(key, None)
                    return

                brand = await BrandRepository(session).get_by_id(pm.brand_id)
                brand_name = brand.name if brand else None
                # Free web scraping only — never call AI for image discovery (saves tokens).
                image_query = default_image_search_query(
                    pm.model_number,
                    brand_name=brand_name,
                    model_name=pm.model_name,
                )
                image_url = await resolve_product_image(
                    model_number=pm.model_number,
                    brand_name=brand_name,
                    model_name=pm.model_name,
                    model_id=str(pm.id),
                    persist_local=True,
                    image_search_query=image_query,
                    max_queries=_BACKGROUND_MAX_QUERIES,
                )
                if not image_url:
                    logger.info(
                        "Background image resolve found nothing for {} ({})",
                        pm.model_number,
                        model_id,
                    )
                    _retry_after[key] = time.monotonic() + _FAILURE_COOLDOWN_SECONDS
                    return

                await repo.update(
                    pm,
                    product_image_url=image_url,
                    actor=AuditActor.system(display_name="Image Resolver", role="system"),
                )
                await session.commit()
                _retry_after.pop(key, None)
                logger.info(
                    "Background image resolve stored image for {} ({})",
                    pm.model_number,
                    model_id,
                )
    except Exception:
        _retry_after[key] = time.monotonic() + _FAILURE_COOLDOWN_SECONDS
        logger.exception("Background image resolve failed for model {}", model_id)


async def schedule_missing_product_image_backfill(*, limit: int = _BACKFILL_BATCH_SIZE) -> int:
    """Queue background resolve for active models that still lack an image.

    Returns how many jobs were newly scheduled. Safe to call from a scheduler —
    does not block on discovery.
    """
    factory = get_session_factory()
    async with factory() as session:
        repo = ProductModelRepository(session)
        model_ids = await repo.list_ids_missing_product_image(limit=max(limit * 3, limit))

    scheduled = 0
    for model_id in model_ids:
        if scheduled >= limit:
            break
        if schedule_product_image_resolve(model_id):
            scheduled += 1
    if scheduled:
        logger.info("Product image backfill scheduled {} model(s)", scheduled)
    return scheduled


async def product_image_backfill_loop() -> None:
    """Periodically backfill missing product images without blocking API traffic."""
    while True:
        if not await sleep_until_next_run(
            "product_image_backfill",
            interval_seconds=_BACKFILL_INTERVAL_SECONDS,
        ):
            return
        try:
            await schedule_missing_product_image_backfill()
        except Exception:
            logger.exception("Product image backfill cycle failed")
