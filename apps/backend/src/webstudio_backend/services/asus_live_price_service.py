"""ASUS-only live price lookup via Gemini search grounding.

Scoped entirely to the ASUS brand. Never raises — every outcome (success,
not found, low confidence, no API key configured, provider error) maps to a
`live_price_status` value and is persisted via
``ProductModelRepository.update_live_price``, which never erases a
previously-successful price on a failed attempt.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.core.config import get_settings
from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.providers.gemini import GeminiProvider

# Accept a price sourced only from ASUS's own domains, regardless of what the
# model claims — an LLM's compliance with prompt instructions is never
# guaranteed, so this is re-checked here rather than trusted at face value.
_ALLOWED_SOURCE_DOMAINS = ("asus.com",)


def _is_asus_domain(source_url: str | None) -> bool:
    if not source_url:
        return False
    try:
        host = (urlparse(source_url).hostname or "").lower()
    except ValueError:
        return False
    return any(host == domain or host.endswith(f".{domain}") for domain in _ALLOWED_SOURCE_DOMAINS)


def _is_asus_brand(brand_name: str | None) -> bool:
    return bool(brand_name) and brand_name.strip().upper() == "ASUS"


async def refresh_asus_live_price(session: AsyncSession, model_id: uuid.UUID) -> str:
    """Refresh one model's live price. Returns the resulting status string.

    No-ops with status "not_applicable" if the model is missing, archived,
    or not an ASUS model — callers do not need to check brand themselves.
    """
    repo = ProductModelRepository(session)
    pm = await repo.get_by_id(model_id)
    if pm is None:
        return "not_applicable"

    brand = await BrandRepository(session).get_by_id(pm.brand_id)
    brand_name = brand.name if brand else None
    if not _is_asus_brand(brand_name):
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

    if not _is_asus_domain(source_url):
        logger.info(
            "ASUS live price for {} rejected — source {!r} is not an asus.com domain",
            pm.model_number,
            source_url,
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

    await repo.update_live_price(pm, status="ok", price=price, source_url=source_url)
    logger.info("ASUS live price updated for {}: {}", pm.model_number, price)
    return "ok"
