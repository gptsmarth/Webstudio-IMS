"""Read-only stock comparison and cached external research."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlsplit

from pydantic import ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.comparison import (
    ComparisonLaptop,
    ComparisonSpec,
    ExternalLaptopRequest,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.database.enums import (
    InventoryStatus,
    ProductCategory,
    ProductModelStatus,
)
from webstudio_backend.infrastructure.database.models.brand import Brand
from webstudio_backend.infrastructure.database.models.inventory_item import InventoryItem
from webstudio_backend.infrastructure.database.models.laptop_comparison_cache import (
    LaptopComparisonCache,
)
from webstudio_backend.infrastructure.database.models.product_model import ProductModel
from webstudio_backend.services.ai.config import resolve_ai_config
from webstudio_backend.services.ai.providers.gemini import GeminiProvider
from webstudio_backend.services.ai.types import AIProviderError
from webstudio_backend.services.product_image_service import is_safe_public_https_url

CACHE_LIFETIME = timedelta(days=30)
UNVERIFIED_MODEL = (
    "Sorry, we couldn't retrieve reliable specifications for this exact laptop model. "
    "Please verify the complete model number and try again."
)
OFFICIAL_IMAGE_DOMAINS = {
    "acer": ("acer.com",),
    "apple": ("apple.com",),
    "asus": ("asus.com",),
    "dell": ("dell.com", "dellcdn.com"),
    "hp": ("hp.com", "hpshopping.in"),
    "lenovo": ("lenovo.com", "lenovo.com.cn"),
    "microsoft": ("microsoft.com",),
    "msi": ("msi.com",),
    "samsung": ("samsung.com",),
}


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def available_count():
    return (
        select(func.count(InventoryItem.id))
        .where(
            InventoryItem.product_model_id == ProductModel.id,
            InventoryItem.status == InventoryStatus.AVAILABLE,
            InventoryItem.is_archived.is_(False),
        )
        .correlate(ProductModel)
        .scalar_subquery()
    )


def stock_laptop_filters(stock_count) -> tuple:
    return (
        ProductModel.status == ProductModelStatus.ACTIVE,
        ProductModel.category == ProductCategory.LAPTOP,
        stock_count > 0,
    )


async def list_stock_laptops(
    session: AsyncSession, *, search: str, page: int, page_size: int
) -> tuple[list[ComparisonLaptop], int]:
    count = available_count()
    query = select(ProductModel, Brand.name, count).join(Brand).where(*stock_laptop_filters(count))
    for term in search.split():
        query = query.where(
            or_(
                Brand.name.icontains(term, autoescape=True),
                ProductModel.model_name.icontains(term, autoescape=True),
                ProductModel.model_number.icontains(term, autoescape=True),
                ProductModel.part_number.icontains(term, autoescape=True),
            )
        )
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = await session.execute(
        query.order_by(Brand.name, ProductModel.model_number, ProductModel.id)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return [_stock_payload(model, brand, quantity) for model, brand, quantity in rows], total or 0


def _stock_payload(model: ProductModel, brand: str, quantity: int) -> ComparisonLaptop:
    storage = " ".join(
        str(value)
        for value in (model.storage_value, model.storage_unit, model.storage_type)
        if value is not None
    )
    specifications = (
        ("Processor", model.cpu),
        ("RAM", f"{model.ram_gb} GB" if model.ram_gb is not None else None),
        ("Storage", storage),
        ("Graphics", model.gpu),
        ("Display", model.display),
        ("Physical design", model.color_options),
        ("Part number", model.part_number),
    )
    image = model.product_image_url
    managed = bool(image and image.startswith("/assets/"))
    return ComparisonLaptop(
        source="inventory",
        model_id=model.id,
        brand=brand,
        model_number=model.model_number,
        model_name=model.model_name,
        managed_image=managed,
        image_url=image if image and not managed and _is_public_https(image) else None,
        available_units=quantity,
        selling_price=str(model.selling_price) if model.selling_price is not None else None,
        saved_notes=model.notes,
        specifications=[
            ComparisonSpec(component=component, detail=detail)
            for component, detail in specifications
            if detail and detail.strip()
        ],
    )


async def purge_expired_research(session: AsyncSession) -> None:
    await session.execute(
        delete(LaptopComparisonCache).where(LaptopComparisonCache.expires_at <= datetime.now(UTC))
    )


async def research_external(
    session: AsyncSession, settings: Settings, lookup: ExternalLaptopRequest
) -> ComparisonLaptop:
    key = (_normalize(lookup.brand), _normalize(lookup.model_number))
    match = (
        LaptopComparisonCache.normalized_brand == key[0],
        LaptopComparisonCache.normalized_model == key[1],
    )
    cached = await _cached_result(session, match)
    if cached is not None:
        return cached

    # Recheck after locking: another request or worker may have just filled the cache.
    lock_id = int.from_bytes(
        hashlib.blake2b(json.dumps(key).encode(), digest_size=8).digest(), "big", signed=True
    )
    await session.execute(select(func.pg_advisory_xact_lock(lock_id)))
    cached = await _cached_result(session, match)
    if cached is not None:
        return cached

    config = await resolve_ai_config(session, settings)
    if not config.enrichment_enabled:
        raise AIProviderError("NOT_CONFIGURED", "External research is disabled.", provider="gemini")
    research = await GeminiProvider(config).research_laptop_comparison(
        lookup.brand, lookup.model_number
    )
    result = _verified_payload(lookup, *research) if research else None
    if result is None:
        raise AIProviderError("NOT_FOUND", UNVERIFIED_MODEL, provider="gemini")

    now = datetime.now(UTC)
    insert_result = insert(LaptopComparisonCache).values(
        normalized_brand=key[0],
        normalized_model=key[1],
        created_at=now,
        expires_at=now + CACHE_LIFETIME,
        payload=result.model_dump(mode="json"),
    )
    await session.execute(
        insert_result.on_conflict_do_update(
            index_elements=["normalized_brand", "normalized_model"],
            set_={
                "payload": insert_result.excluded.payload,
                "created_at": insert_result.excluded.created_at,
                "expires_at": insert_result.excluded.expires_at,
            },
        )
    )
    return result


async def _cached_result(session: AsyncSession, match: tuple) -> ComparisonLaptop | None:
    payload = await session.scalar(
        select(LaptopComparisonCache.payload).where(
            *match, LaptopComparisonCache.expires_at > datetime.now(UTC)
        )
    )
    if payload is None:
        return None
    try:
        result = ComparisonLaptop.model_validate(payload)
    except ValidationError:
        return None
    return result if result.source == "external" else None


def _is_public_https(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return parsed.username is None and parsed.password is None and is_safe_public_https_url(url)
    except ValueError:
        return False


def _text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(char for char in value if char.isprintable() or char in "\n\t").strip()


def _contains_model(text: str, sku: str) -> bool:
    return bool(re.search(rf"(?<![\w/-]){re.escape(_normalize(sku))}(?![\w/-])", _normalize(text)))


def _grounded_exact_model(body: dict[str, Any], evidence: str, brand: str, sku: str) -> bool:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return False
    grounding = candidates[0].get("groundingMetadata")
    if not isinstance(grounding, dict):
        return False
    chunks = grounding.get("groundingChunks")
    if not isinstance(chunks, list):
        return False
    web_chunks = {
        index: chunk["web"]
        for index, chunk in enumerate(chunks)
        if isinstance(chunk, dict)
        and isinstance(chunk.get("web"), dict)
        and isinstance(chunk["web"].get("uri"), str)
        and _is_public_https(chunk["web"]["uri"])
    }
    if not web_chunks:
        return False
    if any(
        _contains_model(_text(chunk.get("title")), sku)
        and _contains_model(_text(chunk.get("title")), brand)
        for chunk in web_chunks.values()
    ):
        return True
    supports = grounding.get("groundingSupports")
    if not isinstance(supports, list):
        return False
    # Google also grounds response spans where the source title is not the full SKU.
    proof = _normalize(evidence)
    for support in supports:
        if not isinstance(support, dict):
            continue
        segment = support.get("segment")
        indexes = support.get("groundingChunkIndices")
        if not isinstance(segment, dict) or not isinstance(indexes, list):
            continue
        span = _normalize(_text(segment.get("text")))
        if proof in span and any(type(index) is int and index in web_chunks for index in indexes):
            return True
    return False


def _verified_payload(
    lookup: ExternalLaptopRequest, raw: dict[str, Any], grounded: dict[str, Any]
) -> ComparisonLaptop | None:
    if raw.get("verified") is not True:
        return None
    if _normalize(_text(raw.get("brand"))) != _normalize(lookup.brand) or _normalize(
        _text(raw.get("model_number"))
    ) != _normalize(lookup.model_number):
        return None
    evidence = _text(raw.get("evidence"))
    if not (
        _contains_model(evidence, lookup.model_number)
        and _contains_model(evidence, lookup.brand)
        and _grounded_exact_model(grounded, evidence, lookup.brand, lookup.model_number)
    ):
        return None
    facts = raw.get("specifications")
    if not isinstance(facts, dict) or not facts or len(facts) > 60:
        return None
    try:
        specifications = [
            ComparisonSpec(component=_text(component), detail=_text(detail))
            for component, detail in facts.items()
            if _normalize(_text(detail))
            not in {"", "not available", "could not be verified", "unknown", "n/a"}
        ]
        if not specifications:
            return None
        return ComparisonLaptop(
            source="external",
            brand=lookup.brand,
            model_number=lookup.model_number,
            model_name=_text(raw.get("model_name")) or None,
            image_url=_exact_image_url(_text(raw.get("image_url")), lookup),
            specifications=specifications,
        )
    except ValidationError:
        return None


def _exact_image_url(url: str, lookup: ExternalLaptopRequest) -> str | None:
    if not url or len(url) > 2048 or not _is_public_https(url):
        return None
    parsed = urlsplit(url)
    host = parsed.hostname or ""
    domains = OFFICIAL_IMAGE_DOMAINS.get(_normalize(lookup.brand), ())
    if not any(host == domain or host.endswith(f".{domain}") for domain in domains):
        return None
    path = unquote(parsed.path)
    if not path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
        return None
    return url if _contains_model(path.rsplit("/", 1)[-1], lookup.model_number) else None
