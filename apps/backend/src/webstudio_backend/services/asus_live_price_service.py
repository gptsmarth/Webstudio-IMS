"""ASUS-only live price lookup via Gemini search grounding.

Scoped entirely to ASUS laptops — accessories (chargers, adapters, mice,
etc.) are explicitly out of scope. Never raises — every outcome (success,
not found, low confidence, no API key configured, provider error) maps to a
`live_price_status` value and is persisted via
``ProductModelRepository.update_live_price``, which never erases a
previously-successful price on a failed attempt.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import httpx
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.database.enums import ProductCategory
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.providers.gemini import GeminiProvider

# Accept a price sourced only from ASUS's own India store, regardless of what
# the model claims — an LLM's compliance with prompt instructions is never
# guaranteed, so this is re-checked here rather than trusted at face value.
# Deliberately narrower than "any asus.com subdomain": asus.com's general
# marketing/spec pages don't carry a real purchasable price, only
# in.store.asus.com does.
_ALLOWED_SOURCE_DOMAINS = ("in.store.asus.com",)

# Google's Search grounding frequently cites sources through its own tracking
# redirect rather than the real page URL (e.g.
# "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AbC123..."),
# by design — the same way Google Search result links work. Naively
# domain-checking that wrapper would reject genuine ASUS-sourced answers
# outright, which is exactly what was happening before this was added: the
# majority of "not an in.store.asus.com domain" rejections were real ASUS
# listings hidden behind this redirect. One HTTP hop resolves it to the real
# target before the domain check runs.
_GROUNDING_REDIRECT_HOST = "vertexaisearch.cloud.google.com"
_REDIRECT_RESOLVE_TIMEOUT_SECONDS = 10.0


def _is_asus_host(host: str | None) -> bool:
    if not host:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in _ALLOWED_SOURCE_DOMAINS)


async def _resolve_grounding_source(source_url: str | None) -> tuple[str | None, str | None]:
    """Returns (resolved_url, resolved_host) for a Gemini grounding citation.

    Any URL that isn't Google's redirect wrapper is returned unchanged. A
    failed resolution (timeout, network error, no Location header) falls
    back to the original URL/host — never raises, and the caller's
    subsequent domain check then simply fails the same way it always did
    before this existed.
    """
    if not source_url:
        return None, None
    try:
        parsed = urlparse(source_url)
    except ValueError:
        return source_url, None
    host = (parsed.hostname or "").lower()
    if host != _GROUNDING_REDIRECT_HOST:
        return source_url, host

    try:
        async with httpx.AsyncClient(
            follow_redirects=False, timeout=_REDIRECT_RESOLVE_TIMEOUT_SECONDS
        ) as client:
            response = await client.get(source_url)
        location = response.headers.get("location")
    except httpx.HTTPError:
        logger.info("Could not resolve Gemini grounding redirect {!r}", source_url)
        return source_url, host

    if not location:
        return source_url, host
    try:
        resolved_host = (urlparse(location).hostname or "").lower()
    except ValueError:
        return source_url, host
    return location, resolved_host


def _is_asus_brand(brand_name: str | None) -> bool:
    return bool(brand_name) and brand_name.strip().upper() == "ASUS"


async def refresh_asus_live_price(session: AsyncSession, model_id: uuid.UUID) -> str:
    """Refresh one model's live price. Returns the resulting status string.

    No-ops with status "not_applicable" if the model is missing, archived,
    not an ASUS model, or not a laptop (accessories are explicitly out of
    scope) — callers do not need to check brand/category themselves.
    """
    repo = ProductModelRepository(session)
    pm = await repo.get_by_id(model_id)
    if pm is None:
        return "not_applicable"

    brand = await BrandRepository(session).get_by_id(pm.brand_id)
    brand_name = brand.name if brand else None
    if not _is_asus_brand(brand_name):
        return "not_applicable"

    if pm.category != ProductCategory.LAPTOP:
        return "not_applicable"

    settings = get_settings()
    ai_config = await resolve_ai_config(session, settings)
    if not ai_config.gemini.api_key.strip():
        await repo.update_live_price(pm, status="not_configured")
        return "not_configured"

    provider = GeminiProvider(ai_config)
    try:
        result = await provider.lookup_live_price(
            pm.model_number,
            brand_name=brand_name,
            model_name=pm.model_name,
        )
    except Exception:
        logger.exception("ASUS live price lookup raised unexpectedly for {}", pm.model_number)
        result = None

    if not result:
        await repo.update_live_price(pm, status="error")
        return "error"

    confidence = str(result.get("confidence") or "").lower()
    raw_price = result.get("price")
    source_url = result.get("source_url")

    if confidence == "low" or raw_price is None:
        await repo.update_live_price(pm, status="not_found")
        return "not_found"

    resolved_url, resolved_host = await _resolve_grounding_source(source_url)
    if not _is_asus_host(resolved_host):
        logger.info(
            "ASUS live price for {} rejected — source {!r} (resolved: {!r}) is not "
            "in.store.asus.com",
            pm.model_number,
            source_url,
            resolved_url,
        )
        await repo.update_live_price(pm, status="not_found")
        return "not_found"

    try:
        price = Decimal(str(raw_price))
    except (InvalidOperation, ValueError, TypeError):
        await repo.update_live_price(pm, status="not_found")
        return "not_found"

    if price <= 0:
        await repo.update_live_price(pm, status="not_found")
        return "not_found"

    await repo.update_live_price(pm, status="ok", price=price, source_url=resolved_url)
    logger.info("ASUS live price updated for {}: {}", pm.model_number, price)
    return "ok"
