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

_PREFERRED_MANUFACTURER_HOST_FRAGMENTS = (
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
    "ssl-product-images.www8-hp.com",
    "psref.lenovo.com",
    "static.lenovo.com",
    "store.storeimages.apple.com",
    "image-us.samsung.com",
)
_RETAILER_HOST_FRAGMENTS = (
    "amazon.",
    "media-amazon.com",
    "ssl-images-amazon.com",
    "flipkart.",
    "rukminim",
    "jiostore",
    "slatic.net",
    "reliancedigital",
    "croma.com",
    "vijaysales",
    "mdcomputers",
)
_PREFERRED_HOST_FRAGMENTS = _PREFERRED_MANUFACTURER_HOST_FRAGMENTS + _RETAILER_HOST_FRAGMENTS
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
    "goodreads.com",
    "barnesandnoble.com",
    "bookdepository",
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
    "kindle",
    "paperback",
    "hardcover",
    "textbook",
    "audiobook",
    "magazine",
    "poster",
    "wallpaper",
    "/books/",
    "/book/",
    "books/",
    "/ebook",
    "ebooks/",
)
_MAX_VALIDATE = 30
_MAX_QUERIES = 18
_SPEC_LOOKUP_MAX_QUERIES = 6
_BACKGROUND_MAX_QUERIES = 18

# Path fragments that are always rejected, even on manufacturer CDNs.
# Keep book/ebook tokens here (not soft-only) so manufacturer hosts cannot
# accept unrelated cover art. Do not add bare "book" — it matches "notebook".
# "banner" stays soft-only so product hero banners on OEM CDNs remain allowed.
_HARD_BLOCKED_PATH_FRAGMENTS = (
    "icon",
    "logo",
    "favicon",
    "sprite",
    "1x1",
    "pixel",
    "kindle",
    "paperback",
    "hardcover",
    "textbook",
    "audiobook",
    "/books/",
    "/book/",
    "books/",
    "/ebook",
    "ebooks/",
)


def _normalize_brand_key(brand_name: str | None) -> str:
    raw = (brand_name or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith("hewlett"):
        return "hp"
    return raw.split()[0]


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

    brand_key = _normalize_brand_key(brand)
    brand_sources = _BRAND_IMAGE_SOURCES.get(brand_key, {})
    site_queries: list[str] = []
    for site in brand_sources.get("sites", ()):
        site_queries.append(f'{site} "{sku}"')
        site_queries.append(f"{site} {sku} product")

    brand_queries: list[str] = []
    if brand:
        brand_queries.append(f'"{sku}" {brand} laptop official product image')
        brand_queries.append(f'"{sku}" {brand} laptop')
        brand_queries.append(f"{brand} {sku} laptop product photo")

    retailer_queries: list[str] = []
    for site in _RETAILER_SITE_QUERIES[:4]:
        retailer_queries.append(f'{site} "{sku}" {brand}'.strip())

    generic_queries: list[str] = []
    if brand and name:
        generic_queries.append(f"{brand} {name} {sku} official")
        generic_queries.append(f"{brand} {name} {sku}")
    generic_queries.append(f'"{sku}" laptop official product')
    generic_queries.append(f'"{sku}" laptop')
    for site in _RETAILER_SITE_QUERIES[4:]:
        generic_queries.append(f"{site} {sku} laptop")
    if brand:
        generic_queries.append(f"{brand} {sku}")

    seen: set[str] = set()
    ordered: list[str] = []
    for query in site_queries + brand_queries + retailer_queries + generic_queries:
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
    brand_key = _normalize_brand_key(brand_name)
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


def text_mentions_model(text: str, model_number: str) -> bool:
    sku = _normalize_sku(model_number)
    if len(sku) < 5:
        return False
    return sku in _normalize_sku(text)


def is_blocked_image_host(url: str, *, brand_name: str | None = None) -> bool:
    host = (urlparse(url).hostname or "").lower()
    path = urlparse(url).path.lower()
    if any(fragment in host for fragment in _BLOCKED_HOST_FRAGMENTS):
        return True
    if is_manufacturer_image_host(url, brand_name=brand_name):
        return any(fragment in path for fragment in _HARD_BLOCKED_PATH_FRAGMENTS)
    return any(fragment in path for fragment in _UNWANTED_PATH_FRAGMENTS)


def is_manufacturer_image_host(url: str, *, brand_name: str | None = None) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not any(fragment in host for fragment in _PREFERRED_MANUFACTURER_HOST_FRAGMENTS):
        return False
    if not brand_name:
        return True
    token = _normalize_brand_key(brand_name)
    if not token:
        return True
    brand_sources = _BRAND_IMAGE_SOURCES.get(token, {})
    brand_domains = brand_sources.get("domains", ())
    if brand_domains and any(domain in host for domain in brand_domains):
        return True
    return token in host


def is_retailer_image_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(fragment in host for fragment in _RETAILER_HOST_FRAGMENTS)


def url_from_trusted_catalog(url: str, *, brand_name: str | None = None) -> bool:
    """Manufacturer CDN/store hosts only — retailer CDNs are not trusted without SKU match."""
    return is_manufacturer_image_host(url, brand_name=brand_name)


def is_relevant_product_image(
    url: str,
    model_number: str,
    *,
    brand_name: str | None = None,
    page_mentions_sku: bool = False,
) -> bool:
    """Accept only images that are clearly tied to the SKU or manufacturer catalog.

    Amazon/Flipkart CDN URLs without the model number in the path are rejected —
    those were the source of random book/unrelated product images.
    """
    if is_blocked_image_host(url, brand_name=brand_name):
        return False
    if url_mentions_model(url, model_number):
        return True
    if is_manufacturer_image_host(url, brand_name=brand_name):
        return True
    # Retailer images are only allowed when scraped from a page that mentions the SKU.
    if page_mentions_sku and is_retailer_image_host(url):
        path = urlparse(url).path.lower()
        if any(token in path for token in ("laptop", "notebook", "product", "catalog")):
            return True
        # Amazon media paths rarely include product words; require stronger page context
        # and a high enough score later (SKU-in-page already required).
        return True
    return False


def score_image_candidate_url(
    url: str, *, brand_name: str | None = None, model_number: str | None = None
) -> int:
    if is_blocked_image_host(url, brand_name=brand_name):
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
    if is_manufacturer_image_host(url, brand_name=brand_name):
        score += 20
    elif is_retailer_image_host(url):
        # Retailer CDN without SKU in URL is weak evidence.
        if model_number and url_mentions_model(url, model_number):
            score += 10
        else:
            score += 2
    else:
        for fragment in _PREFERRED_HOST_FRAGMENTS:
            if fragment in host:
                score += 8
                break
    if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif")):
        score += 6
    if any(
        token in path for token in ("product", "catalog", "notebook", "laptop", "hero", "media")
    ):
        score += 4
    if any(token in path for token in _UNWANTED_PATH_FRAGMENTS):
        score -= 40
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
        page_sku = url_mentions_model(page_url, model_number)
        manufacturer_page = is_manufacturer_image_host(page_url, brand_name=brand_name)

        if page_url.endswith((".jpg", ".jpeg", ".png", ".webp", ".avif")):
            if is_relevant_product_image(
                page_url,
                model_number,
                brand_name=brand_name,
                page_mentions_sku=page_sku,
            ):
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
        page_sku = page_sku or text_mentions_model(html[:80_000], model_number)
        if not page_sku and not manufacturer_page:
            # Skip unrelated search-result pages (common source of book/random images).
            continue

        for url in extract_image_urls_from_html(
            html,
            page_url,
            include_all_images=manufacturer_page,
        ):
            if not is_relevant_product_image(
                url,
                model_number,
                brand_name=brand_name,
                page_mentions_sku=page_sku,
            ):
                continue
            ranked.append(
                (
                    score_image_candidate_url(url, brand_name=brand_name, model_number=model_number)
                    + (6 if page_sku else 0),
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


def resolve_managed_assets_dir(*, create: bool = True) -> Path | None:
    """Resolve the writable root directory for server-managed assets.

    Managed uploads (product images, brand logos) are served to clients under
    ``/assets/...`` via the authenticated image proxy. Their on-disk home
    differs by environment:

    * Production / office servers set ``WEBSTUDIO_DATA_ROOT`` (e.g.
      ``D:\\WEBSTUDIO-IMS``). Assets live under ``<data_root>/assets`` so they
      persist outside the read-only application bundle and survive upgrades.
      The application source tree is not present there, so the repo-relative
      :func:`find_public_assets_dir` cannot be used.
    * Dev / test leave the data root empty, so we fall back to the repository's
      ``apps/desktop/public/assets`` (served by the Vite dev server), preserving
      the previous behaviour exactly.

    Returns ``None`` only when no writable location can be determined.
    """
    from webstudio_backend.core.config import get_settings

    data_root = get_settings().webstudio_data_root.strip()
    if data_root:
        base = Path(data_root) / "assets"
        if create:
            try:
                base.mkdir(parents=True, exist_ok=True)
            except OSError:
                return None
        return base
    return find_public_assets_dir()


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

    assets_root = resolve_managed_assets_dir()
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


def _append_image_candidate(
    ranked: list[tuple[int, str]],
    *,
    url: str | None,
    model_number: str,
    brand_name: str | None,
    bonus: int = 0,
) -> None:
    normalized = _normalize_https_url(url)
    if not normalized:
        return
    if not is_relevant_product_image(normalized, model_number, brand_name=brand_name):
        return
    ranked.append(
        (
            score_image_candidate_url(normalized, brand_name=brand_name, model_number=model_number)
            + bonus,
            normalized,
        )
    )


async def _pick_validated_product_image(
    ranked: list[tuple[int, str]],
    *,
    model_number: str,
    client: httpx.AsyncClient,
    persist_local: bool,
    model_id: str | None,
) -> str | None:
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
        # Retailer CDN hits without SKU in the URL need stronger evidence.
        if is_retailer_image_host(url) and not url_mentions_model(url, model_number) and score < 16:
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
    return None


async def discover_product_image_url(
    *,
    model_number: str,
    brand_name: str | None = None,
    model_name: str | None = None,
    candidate_urls: list[str] | None = None,
    model_id: str | None = None,
    persist_local: bool = False,
    image_search_queries: list[str] | None = None,
    max_queries: int | None = None,
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

    query_limit = max(1, min(max_queries or _SPEC_LOOKUP_MAX_QUERIES, len(queries)))
    queries = queries[:query_limit]

    logger.info(
        "Image discovery for {} using {} search queries (brand={})",
        model_number,
        len(queries),
        brand_name or "unknown",
    )

    ranked: list[tuple[int, str]] = []

    for raw in candidate_urls or []:
        _append_image_candidate(
            ranked,
            url=raw,
            model_number=model_number,
            brand_name=brand_name,
            bonus=8,
        )

    for raw in build_brand_direct_image_candidates(model_number, brand_name=brand_name):
        _append_image_candidate(
            ranked,
            url=raw,
            model_number=model_number,
            brand_name=brand_name,
            bonus=12,
        )

    async with httpx.AsyncClient(
        timeout=20.0,
        follow_redirects=True,
        headers=BROWSER_HEADERS,
    ) as client:
        quick_hit = await _pick_validated_product_image(
            ranked,
            model_number=model_number,
            client=client,
            persist_local=persist_local,
            model_id=model_id,
        )
        if quick_hit:
            return quick_hit

        checked_queries = 0
        for query in queries:
            checked_queries += 1
            for url in await search_bing_image_urls(query, client=client):
                _append_image_candidate(
                    ranked,
                    url=url,
                    model_number=model_number,
                    brand_name=brand_name,
                )

            for url in await search_duckduckgo_image_urls(query, client=client):
                _append_image_candidate(
                    ranked,
                    url=url,
                    model_number=model_number,
                    brand_name=brand_name,
                )

            pages = await search_public_web_for_pages(query, client=client)
            await _rank_page_images_from_urls(
                pages,
                model_number=model_number,
                brand_name=brand_name,
                client=client,
                ranked=ranked,
            )

            hit = await _pick_validated_product_image(
                ranked,
                model_number=model_number,
                client=client,
                persist_local=persist_local,
                model_id=model_id,
            )
            if hit:
                return hit

    logger.info(
        "No product image found for {} (searched {} queries, {} ranked candidates)",
        model_number,
        checked_queries,
        len(ranked),
    )
    return None
