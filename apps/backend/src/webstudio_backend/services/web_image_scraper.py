"""Free public-web image discovery (no paid APIs).

Primary source: Bing Images HTML results (no API key).
Fallback: product-page OpenGraph scraping where sites allow it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from loguru import logger

from webstudio_backend.services.product_image_service import (
    _content_looks_like_image,
    _dedupe_urls,
    _normalize_https_url,
    extract_image_urls_from_html,
    fetch_page_html,
    is_safe_public_https_url,
    is_suspicious_placeholder_image_url,
    search_public_web_for_pages,
    validate_image_url,
)

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": BROWSER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_PREFERRED_HOST_FRAGMENTS = (
    "asus.com",
    "in.store.asus.com",
    "dlcdnwebimgs.asus.com",
    "dell.com",
    "i.dell.com",
    "hp.com",
    "lenovo.com",
    "acer.com",
    "msi.com",
    "samsung.com",
    "apple.com",
    "dlcdn",
    "amazon.",
    "flipkart.",
    "jiostore",
    "slatic.net",
    "cloudfront.net",
    "reliancedigital",
    "croma.com",
    "vijaysales",
)
_BLOCKED_HOST_FRAGMENTS = (
    "scribd.com",
    "flickr.com",
    "wikipedia.org",
    "boredpanda.com",
    "wallpapers.com",
    "wallpaperaccess.com",
    "chzbgr.com",
    "kknews.cc",
    "zhihu.com",
    "epochtimes.com",
    "slideserve.com",
    "slideshare",
    "byjus.com",
    "britannica.com",
    "freepik.com",
    "vecteezy.com",
    "pngtree.com",
    "geomancy.net",
    "bestlifeonline.com",
)
_UNWANTED_PATH_FRAGMENTS = (
    "icon",
    "logo",
    "sprite",
    "avatar",
    "banner",
    "favicon",
    "pixel",
    "1x1",
    "badge",
    "zodiac",
    "meme",
    "hysteresis",
)
_MAX_VALIDATE = 30
_MAX_QUERIES = 18

# Official manufacturer / retailer domains used for site-targeted image search.
_BRAND_IMAGE_SOURCES: dict[str, dict[str, tuple[str, ...]]] = {
    "asus": {
        "sites": ("site:asus.com", "site:in.store.asus.com", "site:dlcdnwebimgs.asus.com"),
        "domains": ("asus.com", "in.store.asus.com", "dlcdnwebimgs.asus.com"),
    },
    "dell": {
        "sites": ("site:dell.com", "site:i.dell.com"),
        "domains": ("dell.com", "i.dell.com"),
    },
    "hp": {
        "sites": ("site:hp.com", "site:ssl-product-images.www8-hp.com"),
        "domains": ("hp.com", "www8-hp.com"),
    },
    "lenovo": {
        "sites": ("site:lenovo.com", "site:psref.lenovo.com"),
        "domains": ("lenovo.com", "static.lenovo.com"),
    },
    "acer": {
        "sites": ("site:acer.com", "site:store.acer.com"),
        "domains": ("acer.com", "store.acer.com"),
    },
    "msi": {
        "sites": ("site:msi.com", "site:store.msi.com"),
        "domains": ("msi.com", "store.msi.com"),
    },
    "apple": {
        "sites": ("site:apple.com",),
        "domains": ("apple.com", "store.storeimages.apple.com"),
    },
    "samsung": {
        "sites": ("site:samsung.com",),
        "domains": ("samsung.com", "image-us.samsung.com"),
    },
}

_RETAILER_SITE_QUERIES = (
    "site:amazon.in",
    "site:amazon.com",
    "site:flipkart.com",
    "site:reliancedigital.in",
    "site:croma.com",
    "site:vijaysales.com",
    "site:mdcomputers.in",
)


def build_product_image_search_queries(
    model_number: str,
    *,
    brand_name: str | None = None,
    model_name: str | None = None,
) -> list[str]:
    sku = model_number.strip()
    brand = (brand_name or "").strip()
    name = (model_name or "").strip()
    queries: list[str] = []

    if brand:
        queries.append(f'"{sku}" {brand} laptop official product image')
        queries.append(f'"{sku}" {brand} laptop')
        queries.append(f"{brand} {sku} laptop product photo")

    brand_key = brand.lower().split()[0] if brand else ""
    brand_sources = _BRAND_IMAGE_SOURCES.get(brand_key, {})
    for site in brand_sources.get("sites", ()):
        queries.append(f'{site} "{sku}"')
        queries.append(f"{site} {sku} product")
    for site in _RETAILER_SITE_QUERIES[:4]:
        queries.append(f'{site} "{sku}" {brand}'.strip())

    if brand and name:
        queries.append(f"{brand} {name} {sku} official")
        queries.append(f"{brand} {name} {sku}")
    queries.append(f'"{sku}" laptop official product')
    queries.append(f'"{sku}" laptop')

    for site in _RETAILER_SITE_QUERIES[4:]:
        queries.append(f"{site} {sku} laptop")

    if brand:
        queries.append(f"{brand} {sku}")

    seen: set[str] = set()
    ordered: list[str] = []
    for query in queries:
        normalized = " ".join(query.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered[:_MAX_QUERIES]


def build_brand_direct_image_candidates(
    model_number: str,
    *,
    brand_name: str | None = None,
) -> list[str]:
    """Predictable manufacturer store CDN paths (no API key required)."""
    sku = model_number.strip().lower()
    if len(sku) < 4:
        return []
    brand_key = (brand_name or "").strip().lower().split()[0]
    candidates: list[str] = []

    if brand_key == "asus":
        base = f"https://in.store.asus.com/media/catalog/product/{sku[0]}/{sku[1]}/{sku}_1_"
        candidates.extend(f"{base}{ext}" for ext in (".jpg", ".png", ".webp"))
        family = sku.split("-", 1)[0]
        if family != sku:
            family_base = f"https://in.store.asus.com/media/catalog/product/{family[0]}/{family[1]}/{family}_1_"
            candidates.extend(f"{family_base}{ext}" for ext in (".jpg", ".png"))

    return _dedupe_urls(candidates)


def _normalize_sku(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def url_mentions_model(url: str, model_number: str) -> bool:
    sku = _normalize_sku(model_number)
    if len(sku) < 5:
        return False
    return sku in _normalize_sku(url)


def is_blocked_image_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path.lower()
    if any(fragment in host for fragment in _BLOCKED_HOST_FRAGMENTS):
        return True
    return any(fragment in path for fragment in _UNWANTED_PATH_FRAGMENTS)


def url_from_trusted_catalog(url: str, *, brand_name: str | None = None) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not any(fragment in host for fragment in _PREFERRED_HOST_FRAGMENTS):
        return False
    if brand_name:
        token = brand_name.lower().split()[0]
        if token and (token in host or token in url.lower()):
            return True
    return any(
        fragment in host
        for fragment in (
            "dlcdn",
            "asus.com",
            "dell.com",
            "hp.com",
            "lenovo.com",
            "acer.com",
            "amazon.",
            "flipkart.",
        )
    )


def is_relevant_product_image(
    url: str, model_number: str, *, brand_name: str | None = None
) -> bool:
    if is_blocked_image_host(url):
        return False
    if url_mentions_model(url, model_number):
        return True
    return url_from_trusted_catalog(url, brand_name=brand_name)


def score_image_candidate_url(
    url: str, *, brand_name: str | None = None, model_number: str | None = None
) -> int:
    if is_blocked_image_host(url):
        return -100
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path.lower()
    score = 0
    if brand_name:
        token = brand_name.lower().split()[0]
        if token and token in host:
            score += 25
    if model_number and url_mentions_model(url, model_number):
        score += 40
    for fragment in _PREFERRED_HOST_FRAGMENTS:
        if fragment in host:
            score += 12
    if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")):
        score += 6
    if any(
        token in path for token in ("product", "catalog", "notebook", "laptop", "hero", "media")
    ):
        score += 4
    if any(token in path for token in _UNWANTED_PATH_FRAGMENTS):
        score -= 30
    if "thumb" in path or "thumbnail" in path:
        score -= 5
    return score


async def _is_usable_product_image(url: str, *, client: httpx.AsyncClient) -> bool:
    """Validate image URL and reject known manufacturer placeholder assets."""
    normalized = _normalize_https_url(url)
    if not normalized or not await validate_image_url(normalized, client=client):
        return False

    host = (urlparse(normalized).hostname or "").lower()
    if "in.store.asus.com" not in host:
        return True

    try:
        response = await client.get(
            normalized,
            headers={**BROWSER_HEADERS, "Range": "bytes=0-65535"},
        )
    except httpx.HTTPError:
        return False
    if response.status_code not in {200, 206}:
        return False
    content = response.content
    # ASUS India store serves a generic 1200x1200 "coming soon" PNG (~21 KB) for missing SKUs.
    if len(content) < 30_000 and content[:8] == b"\x89PNG\r\n\x1a\n":
        return False
    return True


async def _rank_page_images_from_urls(
    page_urls: list[str],
    *,
    model_number: str,
    brand_name: str | None,
    client: httpx.AsyncClient,
    ranked: list[tuple[int, str]],
) -> None:
    for page_url in page_urls:
        if page_url.endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
            if is_relevant_product_image(page_url, model_number, brand_name=brand_name):
                ranked.append(
                    (
                        score_image_candidate_url(
                            page_url, brand_name=brand_name, model_number=model_number
                        ),
                        page_url,
                    )
                )
            continue
        html = await fetch_page_html(page_url, client=client)
        if not html:
            continue
        for url in extract_image_urls_from_html(html, page_url):
            if not is_relevant_product_image(url, model_number, brand_name=brand_name):
                continue
            ranked.append(
                (
                    score_image_candidate_url(
                        url, brand_name=brand_name, model_number=model_number
                    ),
                    url,
                )
            )


async def search_bing_image_urls(
    query: str,
    *,
    client: httpx.AsyncClient,
    limit: int = 24,
) -> list[str]:
    try:
        response = await client.get(
            "https://www.bing.com/images/search",
            params={"q": query, "form": "HDRSC2"},
            headers=BROWSER_HEADERS,
        )
        if response.status_code >= 400:
            return []
        urls = re.findall(r"murl&quot;:&quot;(https://[^&]+?)&quot;", response.text)
        if not urls:
            urls = re.findall(r'"murl":"(https://[^"]+)"', response.text)
        return _dedupe_urls(urls)[:limit]
    except httpx.HTTPError as exc:
        logger.debug("Bing image search failed for '{}': {}", query, type(exc).__name__)
        return []


async def _fetch_duckduckgo_vqd(query: str, *, client: httpx.AsyncClient) -> str | None:
    try:
        response = await client.get(
            "https://duckduckgo.com/",
            params={"q": query},
            headers=BROWSER_HEADERS,
        )
        if response.status_code >= 400:
            return None
        match = re.search(r"vqd=['\"]?([^&'\"]+)", response.text)
        return match.group(1) if match else None
    except httpx.HTTPError:
        return None


async def search_duckduckgo_image_urls(
    query: str,
    *,
    client: httpx.AsyncClient,
    limit: int = 12,
) -> list[str]:
    vqd = await _fetch_duckduckgo_vqd(query, client=client)
    if not vqd:
        return []
    try:
        response = await client.get(
            "https://duckduckgo.com/i.js",
            params={"l": "wt-wt", "o": "json", "q": query, "vqd": vqd},
            headers={**BROWSER_HEADERS, "Referer": "https://duckduckgo.com/"},
        )
        if response.status_code >= 400:
            return []
        payload = json.loads(response.text)
    except (httpx.HTTPError, json.JSONDecodeError):
        return []

    urls: list[str] = []
    results = payload.get("results")
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            for key in ("image", "thumbnail", "url"):
                raw = item.get(key)
                if isinstance(raw, str):
                    urls.append(raw)
    return _dedupe_urls(urls)[:limit]


def find_public_assets_dir() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "apps" / "desktop" / "public" / "assets"
        if candidate.is_dir():
            return candidate
    return None


def _extension_for_content_type(content_type: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
        "image/avif": "avif",
    }
    return mapping.get(content_type.split(";")[0].strip().lower(), "jpg")


async def persist_product_image_file(
    url: str,
    *,
    model_id: str,
    client: httpx.AsyncClient,
) -> str | None:
    normalized = _normalize_https_url(url)
    if not normalized:
        return None

    assets_root = find_public_assets_dir()
    if assets_root is None:
        return normalized

    try:
        response = await client.get(normalized, headers=BROWSER_HEADERS)
    except httpx.HTTPError:
        return None
    if response.status_code >= 400:
        return None

    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if not _content_looks_like_image(response.content[:16], content_type):
        return None

    folder = assets_root / "product-images"
    folder.mkdir(parents=True, exist_ok=True)
    ext = _extension_for_content_type(content_type)
    filename = f"{model_id}.{ext}"
    (folder / filename).write_bytes(response.content)
    return f"/assets/product-images/{filename}"


async def discover_product_image_url(
    *,
    model_number: str,
    brand_name: str | None = None,
    model_name: str | None = None,
    candidate_urls: list[str] | None = None,
    model_id: str | None = None,
    persist_local: bool = False,
    image_search_queries: list[str] | None = None,
) -> str | None:
    """Discover product images across manufacturer CDNs, Bing, DuckDuckGo, and retailer pages."""
    queries = build_product_image_search_queries(
        model_number,
        brand_name=brand_name,
        model_name=model_name,
    )
    if image_search_queries:
        seen = set(queries)
        for query in image_search_queries:
            normalized = " ".join(query.split())
            if normalized and normalized not in seen:
                seen.add(normalized)
                queries.insert(0, normalized)

    logger.info(
        "Image discovery for {} using {} search queries (brand={})",
        model_number,
        len(queries),
        brand_name or "unknown",
    )

    ranked: list[tuple[int, str]] = []

    for raw in candidate_urls or []:
        url = _normalize_https_url(raw)
        if url and is_relevant_product_image(url, model_number, brand_name=brand_name):
            ranked.append(
                (
                    score_image_candidate_url(url, brand_name=brand_name, model_number=model_number)
                    + 8,
                    url,
                )
            )

    for raw in build_brand_direct_image_candidates(model_number, brand_name=brand_name):
        url = _normalize_https_url(raw)
        if url:
            ranked.append(
                (
                    score_image_candidate_url(url, brand_name=brand_name, model_number=model_number)
                    + 10,
                    url,
                )
            )

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers=BROWSER_HEADERS,
    ) as client:
        for query in queries:
            for url in await search_bing_image_urls(query, client=client):
                if not is_relevant_product_image(url, model_number, brand_name=brand_name):
                    continue
                ranked.append(
                    (
                        score_image_candidate_url(
                            url, brand_name=brand_name, model_number=model_number
                        ),
                        url,
                    )
                )

        for query in queries:
            for url in await search_duckduckgo_image_urls(query, client=client):
                if not is_relevant_product_image(url, model_number, brand_name=brand_name):
                    continue
                ranked.append(
                    (
                        score_image_candidate_url(
                            url, brand_name=brand_name, model_number=model_number
                        ),
                        url,
                    )
                )

        for query in queries:
            pages = await search_public_web_for_pages(query, client=client)
            await _rank_page_images_from_urls(
                pages,
                model_number=model_number,
                brand_name=brand_name,
                client=client,
                ranked=ranked,
            )

        ranked.sort(key=lambda row: row[0], reverse=True)
        seen: set[str] = set()
        checked = 0
        for score, url in ranked:
            if checked >= _MAX_VALIDATE:
                break
            key = url.rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            if score < 10:
                continue
            if not is_safe_public_https_url(url) or is_suspicious_placeholder_image_url(url):
                continue
            checked += 1
            if not await _is_usable_product_image(url, client=client):
                continue
            logger.info(
                "Product image discovered for {} (score={}, host={})",
                model_number,
                score,
                urlparse(url).hostname,
            )
            if persist_local and model_id:
                stored = await persist_product_image_file(url, model_id=model_id, client=client)
                return stored or url
            return url

    logger.info(
        "No product image found for {} (checked {} ranked candidates)", model_number, checked
    )
    return None
