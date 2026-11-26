"""Read-only stock comparison and cached external research."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.api.schemas.comparison import (
    ComparisonLaptop,
    ComparisonSpec,
    ExternalLaptopRequest,
)
from webstudio_backend.api.schemas.laptop_specification import (
    MAX_DETAILED_SPECIFICATIONS,
    detailed_specifications,
    documented_detail,
)
from webstudio_backend.core.config import Settings
from webstudio_backend.infrastructure.audit.audit_actor import AuditActor
from webstudio_backend.infrastructure.audit.audit_recorder import AuditRecorder
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
from webstudio_backend.services.comparison_processor import (
    exact_chip,
    has_cpu_details,
    has_cpu_totals,
    processor_facts,
    processor_text,
    with_processor_facts,
)
from webstudio_backend.services.product_image_service import is_safe_public_https_url

CACHE_LIFETIME = timedelta(days=30)
INVENTORY_RESEARCH_RETRY = timedelta(days=1)
PROCESSOR_CACHE_NAMESPACE = ":cpu:"
PROCESSOR_SPECS = TypeAdapter(list[ComparisonSpec])
MAIN_HARDWARE = re.compile(
    r"^(processor|cpu(?! (cores|threads|core layout|cache|max turbo)\b)|"
    r"ram|memory|storage|ssd|display|screen|graphics|gpu)\b",
    re.I,
)
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
    note_labels = {
        label.strip().casefold()
        for line in (model.notes or "").split("\n---\n", 1)[0].splitlines()
        for label, separator, value in [line.partition(":")]
        if separator and value.strip()
    }
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
        specifications_pending=_needs_inventory_research(model),
        specifications=with_processor_facts(
            [
                ComparisonSpec(component=component, detail=detail)
                for component, detail in specifications
                if detail and detail.strip()
            ]
            + [
                ComparisonSpec.model_validate(spec)
                for spec in (model.detailed_specifications or [])
                if spec["component"].casefold() not in note_labels
            ]
        ),
    )


def _needs_inventory_research(model: ProductModel) -> bool:
    return model.specifications_researched_at is None and (
        model.specifications_retry_at is None or model.specifications_retry_at <= datetime.now(UTC)
    )


async def purge_expired_research(session: AsyncSession) -> None:
    await session.execute(
        delete(LaptopComparisonCache).where(LaptopComparisonCache.expires_at <= datetime.now(UTC))
    )


async def research_external(
    session: AsyncSession,
    settings: Settings,
    lookup: ExternalLaptopRequest,
    *,
    refresh_sparse: bool = False,
) -> ComparisonLaptop:
    key = (_normalize(lookup.brand), _normalize(lookup.model_number))
    match = (
        LaptopComparisonCache.normalized_brand == key[0],
        LaptopComparisonCache.normalized_model == key[1],
    )
    cached = await _cached_result(session, match, refresh_sparse=refresh_sparse)
    if cached is not None:
        return cached

    # Recheck after locking: another request or worker may have just filled the cache.
    await session.execute(select(func.pg_advisory_xact_lock(_lock_id(key))))
    cached = await _cached_result(session, match, refresh_sparse=refresh_sparse)
    if cached is not None:
        return cached

    config = await resolve_ai_config(session, settings)
    if not config.enrichment_enabled:
        raise AIProviderError("NOT_CONFIGURED", "External research is disabled.", provider="gemini")
    provider = GeminiProvider(config)
    async with asyncio.timeout(60):
        research = await provider.research_laptop_comparison(
            lookup.brand,
            lookup.model_number,
            verify=lambda raw, body: _verified_payload(lookup, raw, body) is not None,
        )
    result = _verified_payload(lookup, *research) if research else None
    if result is None:
        raise AIProviderError("NOT_FOUND", UNVERIFIED_MODEL, provider="gemini")

    chip = exact_chip(processor_text(result.specifications))
    if chip and not has_cpu_details(processor_facts(result.specifications)):
        extra = await _research_processor(session, provider, chip)
        result.specifications = _supplement_processor(result.specifications, extra)
    await _save_research(session, key, result.model_dump(mode="json"))
    return result


def _lock_id(key: tuple[str, str]) -> int:
    return int.from_bytes(
        hashlib.blake2b(json.dumps(key).encode(), digest_size=8).digest(), "big", signed=True
    )


async def _save_research(session: AsyncSession, key: tuple[str, str], payload: Any) -> None:
    now = datetime.now(UTC)
    insert_result = insert(LaptopComparisonCache).values(
        normalized_brand=key[0],
        normalized_model=key[1],
        created_at=now,
        expires_at=now + CACHE_LIFETIME,
        payload=payload,
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


async def _cached_payload(session: AsyncSession, *match) -> Any:
    return await session.scalar(
        select(LaptopComparisonCache.payload).where(
            *match, LaptopComparisonCache.expires_at > datetime.now(UTC)
        )
    )


async def _cached_result(
    session: AsyncSession, match: tuple, *, refresh_sparse: bool = False
) -> ComparisonLaptop | None:
    payload = await _cached_payload(session, *match)
    if payload is None:
        return None
    try:
        result = ComparisonLaptop.model_validate(payload)
    except ValidationError:
        return None
    if result.source != "external" or not _has_hardware(result.specifications):
        return None
    if refresh_sparse:
        supplemental = _inventory_facts(result.specifications, None, "", None)
        if not detailed_specifications({spec.component: spec.detail for spec in supplemental}):
            return None
    result.specifications = with_processor_facts(result.specifications)
    return result


async def inventory_processor(
    session: AsyncSession, settings: Settings, model_id: UUID
) -> list[ComparisonSpec] | None:
    count = available_count()
    row = (
        await session.execute(
            select(ProductModel, Brand.name)
            .join(Brand)
            .where(ProductModel.id == model_id, *stock_laptop_filters(count))
        )
    ).one_or_none()
    if row is None:
        return None
    model, brand = row
    saved = [ComparisonSpec(component="Processor", detail=model.cpu)] if model.cpu else []
    found = with_processor_facts(saved)[len(saved) :]
    if has_cpu_totals(processor_facts(found)):
        return found
    chip = exact_chip(model.cpu or "")
    if chip:
        config = await resolve_ai_config(session, settings)
        if config.enrichment_enabled:
            return _supplement_processor(
                found, await _research_processor(session, GeminiProvider(config), chip)
            )
        return found

    try:
        lookup = ExternalLaptopRequest(brand=brand, model_number=model.model_number)
        laptop = await research_external(session, settings, lookup)
    except (ValidationError, AIProviderError, TimeoutError):
        return found
    researched = processor_text(laptop.specifications)
    if not exact_chip(researched):
        return found
    return [
        ComparisonSpec(component="Processor", detail=researched),
        *_supplement_processor(
            found,
            [
                ComparisonSpec(component=label, detail=value)
                for label, value in processor_facts(laptop.specifications).items()
            ],
        ),
    ]


def _inventory_configuration(model: ProductModel) -> tuple:
    return (
        model.brand_id,
        model.model_number,
        model.cpu,
        model.gpu,
        model.ram_gb,
        model.storage_value,
        model.storage_type,
        model.storage_unit,
        model.display,
    )


async def inventory_specifications(
    session: AsyncSession, settings: Settings, model_id: UUID
) -> ComparisonLaptop | None:
    count = available_count()
    query = (
        select(ProductModel, Brand.name, count)
        .join(Brand)
        .where(ProductModel.id == model_id, *stock_laptop_filters(count))
        .execution_options(populate_existing=True)
    )
    row = (await session.execute(query)).one_or_none()
    if row is None:
        return None
    model, brand, quantity = row
    if not _needs_inventory_research(model):
        return _stock_payload(model, brand, quantity)
    await session.execute(
        select(func.pg_advisory_xact_lock(_lock_id((":inventory:", str(model_id)))))
    )
    row = (await session.execute(query)).one_or_none()
    if row is None:
        return None
    model, brand, quantity = row
    if not _needs_inventory_research(model):
        return _stock_payload(model, brand, quantity)

    configuration = _inventory_configuration(model)
    saved_cpu = model.cpu or ""
    saved_chip = exact_chip(saved_cpu)
    researched = None
    specs = []
    try:
        lookup = ExternalLaptopRequest(brand=brand, model_number=model.model_number)
        researched = await research_external(session, settings, lookup, refresh_sparse=True)
        specs = researched.specifications
    except (ValidationError, AIProviderError, TimeoutError):
        pass

    researched_cpu = processor_text(specs)
    researched_chip = exact_chip(researched_cpu)
    supplemental = _inventory_facts(specs, saved_chip, researched_cpu, researched_chip)
    if saved_chip and not has_cpu_details(processor_facts(supplemental)):
        config = await resolve_ai_config(session, settings)
        if config.enrichment_enabled:
            chip_specs = await _research_processor(session, GeminiProvider(config), saved_chip)
            supplemental = _supplement_processor(supplemental, chip_specs)

    # The lookup may take several seconds. Check for a concurrent hardware edit
    # before attaching facts and serialize the short write with other updates.
    latest = (await session.execute(query.with_for_update(of=ProductModel))).one_or_none()
    if latest is None:
        return None
    model, brand, quantity = latest
    if _inventory_configuration(model) == configuration:
        previous = model.detailed_specifications or []
        facts = {spec["component"].casefold(): spec for spec in previous}
        for spec in detailed_specifications(
            {entry.component: entry.detail for entry in supplemental}
        ):
            facts.setdefault(spec.component.casefold(), spec.model_dump())
        now = datetime.now(UTC)
        combined = list(facts.values())[:MAX_DETAILED_SPECIFICATIONS]
        if combined != previous:
            model.detailed_specifications = combined
            await AuditRecorder(session).record_product_model_field_update(
                model,
                field_name="detailed_specifications",
                old_value={"count": len(previous)},
                new_value={"count": len(combined)},
                actor=AuditActor.system(),
            )
        if researched is not None and supplemental:
            model.specifications_researched_at = now
            model.specifications_retry_at = None
        else:
            model.specifications_retry_at = now + INVENTORY_RESEARCH_RETRY
        await session.flush()
    return _stock_payload(model, brand, quantity)


def _inventory_facts(
    specs: list[ComparisonSpec],
    saved_chip: str | None,
    researched_cpu: str,
    researched_chip: str | None,
) -> list[ComparisonSpec]:
    primary = {
        "processor",
        "cpu",
        "ram",
        "ram capacity",
        "memory",
        "memory capacity",
        "storage",
        "storage capacity",
        "storage drives",
        "graphics",
        "gpu",
        "graphics gpu",
        "display",
        "screen",
        "physical design",
        "colors",
        "colour",
    }
    cpu_matches = not saved_chip or saved_chip == researched_chip
    useful = [
        spec
        for spec in specs
        if spec.component.casefold() not in primary
        and (
            cpu_matches
            or not spec.component.casefold().startswith(
                ("cpu", "processor", "cores", "threads", "cache")
            )
        )
    ]
    if not saved_chip and researched_cpu:
        useful.insert(0, ComparisonSpec(component="Processor model", detail=researched_cpu))
    return with_processor_facts(useful)


def _supplement_processor(
    existing: list[ComparisonSpec], extra: list[ComparisonSpec]
) -> list[ComparisonSpec]:
    known = processor_facts(existing)
    additions = {spec.component: spec for spec in extra if spec.component not in known}
    return [
        *(spec for spec in existing if spec.component not in additions),
        *additions.values(),
    ][:60]


async def _research_processor(
    session: AsyncSession, provider: GeminiProvider, chip: str
) -> list[ComparisonSpec]:
    key = (PROCESSOR_CACHE_NAMESPACE, chip)
    match = (
        LaptopComparisonCache.normalized_brand == key[0],
        LaptopComparisonCache.normalized_model == key[1],
    )
    cached = await _cached_payload(session, *match)
    if cached is not None:
        try:
            return PROCESSOR_SPECS.validate_python(cached)
        except ValidationError:
            pass
    # Optional detail should not wait behind another request researching the same chip.
    if not await session.scalar(select(func.pg_try_advisory_xact_lock(_lock_id(key)))):
        return []

    def validated(raw: dict[str, Any], body: dict[str, Any]) -> list[ComparisonSpec]:
        if exact_chip(_text(raw.get("processor"))) != chip:
            return []
        domain = "intel.com" if chip.startswith("intel ") else "amd.com"
        chunks, supports = _grounding(body)
        official = {index for index, chunk in chunks.items() if _official_chunk(chunk, (domain,))}
        if not any(
            exact_chip(_text(chunks[index].get("title"))) == chip for index in official
        ) and not any(
            exact_chip(span) == chip and bool(official.intersection(indexes))
            for span, indexes in supports
        ):
            return []
        return [
            ComparisonSpec(component=label, detail=value)
            for label, value in processor_facts(_specifications(raw.get("specifications"))).items()
        ]

    try:
        async with asyncio.timeout(12):
            result = await provider.research_comparison_processor(
                chip, verify=lambda raw, body: bool(validated(raw, body))
            )
    except (AIProviderError, TimeoutError):
        return []
    facts = validated(*result) if result else []
    if facts:
        await _save_research(session, key, [spec.model_dump(mode="json") for spec in facts])
    return facts


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


def _grounding(
    body: dict[str, Any],
) -> tuple[dict[int, dict[str, Any]], list[tuple[str, set[int]]]]:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], dict):
        return {}, []
    candidate = candidates[0]
    grounding = candidate.get("groundingMetadata")
    if not isinstance(grounding, dict):
        return {}, []
    chunks = grounding.get("groundingChunks")
    if not isinstance(chunks, list):
        return {}, []
    web_chunks = {
        index: chunk["web"]
        for index, chunk in enumerate(chunks)
        if isinstance(chunk, dict)
        and isinstance(chunk.get("web"), dict)
        and isinstance(chunk["web"].get("uri"), str)
        and _is_public_https(chunk["web"]["uri"])
    }
    supports = grounding.get("groundingSupports")
    if not isinstance(supports, list):
        return web_chunks, []
    citations = []
    for support in supports:
        if not isinstance(support, dict):
            continue
        segment = support.get("segment")
        indexes = support.get("groundingChunkIndices")
        if not isinstance(segment, dict) or not isinstance(indexes, list):
            continue
        cited = {index for index in indexes if type(index) is int and index in web_chunks}
        if cited:
            citations.append((_citation_text(segment, candidate), cited))
    return web_chunks, citations


def _citation_text(segment: dict[str, Any], candidate: dict[str, Any]) -> str:
    if text := _text(segment.get("text")):
        return text
    content = candidate.get("content")
    parts = content.get("parts") if isinstance(content, dict) else None
    index = segment.get("partIndex", 0)
    if not isinstance(parts, list) or type(index) is not int or not 0 <= index < len(parts):
        return ""
    part = parts[index]
    if not isinstance(part, dict) or part.get("thought") is True:
        return ""
    start, end = segment.get("startIndex", 0), segment.get("endIndex")
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        return ""
    value = part.get("text")
    return value.encode()[start:end].decode(errors="ignore") if isinstance(value, str) else ""


def _matches_domain(host: str, domains: tuple[str, ...]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _official_chunk(chunk: dict[str, Any], domains: tuple[str, ...]) -> bool:
    host = urlsplit(chunk["uri"]).hostname or ""
    return _matches_domain(host, domains) or (
        host == "vertexaisearch.cloud.google.com"
        and _matches_domain(_text(chunk.get("title")).lower(), domains)
    )


def _grounded_exact_model(body: dict[str, Any], brand: str, sku: str) -> bool:
    chunks, supports = _grounding(body)
    domains = OFFICIAL_IMAGE_DOMAINS.get(_normalize(brand), ())
    official = {index for index, chunk in chunks.items() if _official_chunk(chunk, domains)}

    def matches(text: str) -> bool:
        return _contains_model(text, sku) and _contains_model(text, brand)

    for chunk in chunks.values():
        title = _text(chunk.get("title"))
        if matches(title):
            return True
        url = urlsplit(chunk["uri"])
        if not _matches_domain(url.hostname or "", domains):
            continue
        if _contains_model(title, sku):
            return True
        slug = _normalize(unquote(url.path.rsplit("/", 1)[-1]))
        slug = re.sub(r"\.(?:html?|aspx?)$", "", slug)
        normalized_sku = re.escape(_normalize(sku).replace(" ", "-"))
        if re.search(rf"(?:^|-){normalized_sku}(?:-copilot-pc)?$", slug):
            return True
    return any(
        matches(span) or (_contains_model(span, sku) and bool(indexes & official))
        for span, indexes in supports
    )


def _specifications(facts: Any) -> list[ComparisonSpec]:
    if not isinstance(facts, dict) or len(facts) > 60:
        return []
    specifications = []
    for component, detail in facts.items():
        label, value = _text(component), _text(detail)
        if (
            not label
            or not documented_detail(value)
            or _normalize(value)
            in {
                "",
                "not available",
                "could not be verified",
                "unknown",
                "n/a",
                "null",
                "not published",
                "not specified",
                "unverified",
                "unavailable",
                "-",
                "—",
            }
        ):
            continue
        try:
            specifications.append(ComparisonSpec(component=label, detail=value))
        except ValidationError:
            continue
    return specifications


def _has_hardware(specifications: list[ComparisonSpec]) -> bool:
    return any(
        MAIN_HARDWARE.match(spec.component)
        for spec in _specifications({spec.component: spec.detail for spec in specifications})
    )


def _verified_payload(
    lookup: ExternalLaptopRequest, raw: dict[str, Any], grounded: dict[str, Any]
) -> ComparisonLaptop | None:
    if raw.get("verified") is not True:
        return None
    if _normalize(_text(raw.get("brand"))) != _normalize(lookup.brand) or _normalize(
        _text(raw.get("model_number"))
    ) != _normalize(lookup.model_number):
        return None
    if not _grounded_exact_model(grounded, lookup.brand, lookup.model_number):
        return None
    specifications = with_processor_facts(_specifications(raw.get("specifications")))
    if not _has_hardware(specifications):
        return None
    try:
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
    if not _matches_domain(host, domains):
        return None
    path = unquote(parsed.path)
    if not path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
        return None
    return url if _contains_model(path.rsplit("/", 1)[-1], lookup.model_number) else None
