"""Resolve and validate laptop product image URLs from the public web."""

from __future__ import annotations

import ipaddress
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx
from loguru import logger

if TYPE_CHECKING:
    from webstudio_backend.services.gemini_spec_service import GeminiSpecService

IMAGE_CONTENT_TYPES = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/avif",
)
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")
USER_AGENT = (
    "Mozilla/5.0 (compatible; WebstudioIMS/1.0; +https://webstudio.local/product-image-fetch)"
)
MAX_PAGE_FETCHES = 4
MAX_CANDIDATES = 12


def _normalize_https_url(url: str | None) -> str | None:
    if not url:
        return None
    text = str(url).strip()
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    if text.startswith("//"):
        text = f"https:{text}"
    if not text.startswith("https://"):
        return None
    return text[:512]


def is_safe_public_https_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False
    host = parsed.hostname
    if not host:
        return False
    lowered = host.lower()
    if lowered in {"localhost", "127.0.0.1", "0.0.0.0"} or lowered.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(lowered)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False
    except ValueError:
        pass
    return True


def _looks_like_image_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


def _dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in urls:
        url = _normalize_https_url(raw)
        if not url or not is_safe_public_https_url(url):
            continue
        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        ordered.append(url)
        if len(ordered) >= MAX_CANDIDATES:
            break
    return ordered


def extract_grounding_page_urls(body: dict[str, Any] | None) -> list[str]:
    if not body:
        return []
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return []
    metadata = candidates[0].get("groundingMetadata") if isinstance(candidates[0], dict) else None
    if not isinstance(metadata, dict):
        return []

    urls: list[str] = []
    chunks = metadata.get("groundingChunks")
    if isinstance(chunks, list):
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            web = chunk.get("web")
            if isinstance(web, dict):
                uri = web.get("uri")
                if isinstance(uri, str):
                    urls.append(uri)
    return _dedupe_urls(urls)


def extract_image_urls_from_html(html: str, page_url: str) -> list[str]:
    urls: list[str] = []
    patterns = (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            urls.append(match.group(1).strip())

    for match in re.finditer(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    ):
        src = match.group(1).strip()
        lowered = src.lower()
        if any(token in lowered for token in ("product", "laptop", "notebook", "hero", "gallery")):
            urls.append(src)

    resolved: list[str] = []
    page = urlparse(page_url)
    origin = f"{page.scheme}://{page.netloc}"
    for raw in urls:
        if raw.startswith("//"):
            resolved.append(f"https:{raw}")
        elif raw.startswith("/"):
            resolved.append(f"{origin}{raw}")
        elif raw.startswith("http"):
            resolved.append(raw)
    return _dedupe_urls(resolved)


async def validate_image_url(url: str, *, client: httpx.AsyncClient | None = None) -> bool:
    normalized = _normalize_https_url(url)
    if not normalized or not is_safe_public_https_url(normalized):
        return False

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    try:
        response = await http.head(normalized)
        if response.status_code >= 400:
            response = await http.get(normalized, headers={"Range": "bytes=0-8191"})
        if response.status_code >= 400:
            return False
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type in IMAGE_CONTENT_TYPES:
            return True
        if _looks_like_image_url(normalized):
            return True
        return False
    except httpx.HTTPError:
        return False
    finally:
        if owns_client:
            await http.aclose()


async def fetch_page_html(url: str, *, client: httpx.AsyncClient) -> str | None:
    if not is_safe_public_https_url(url):
        return None
    try:
        response = await client.get(url, headers={"User-Agent": USER_AGENT})
        if response.status_code >= 400:
            return None
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "text/" not in content_type:
            return None
        return response.text
    except httpx.HTTPError as exc:
        logger.debug("Product page fetch failed for {}: {}", url, type(exc).__name__)
        return None


async def resolve_product_image(
    *,
    model_number: str,
    brand_name: str | None = None,
    model_name: str | None = None,
    candidate_url: str | None = None,
    grounding_body: dict[str, Any] | None = None,
    gemini_service: GeminiSpecService | None = None,
) -> str | None:
    """Find a loadable HTTPS product image URL for an exact model number."""
    candidates: list[str] = []
    if candidate_url:
        candidates.append(candidate_url)

    for page_url in extract_grounding_page_urls(grounding_body):
        if _looks_like_image_url(page_url):
            candidates.append(page_url)

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        page_urls = extract_grounding_page_urls(grounding_body)
        for page_url in page_urls[:MAX_PAGE_FETCHES]:
            if _looks_like_image_url(page_url):
                continue
            html = await fetch_page_html(page_url, client=client)
            if html:
                candidates.extend(extract_image_urls_from_html(html, page_url))

        for url in _dedupe_urls(candidates):
            if await validate_image_url(url, client=client):
                return url

        if gemini_service and gemini_service.is_configured:
            looked_up = await gemini_service.lookup_product_image(
                model_number,
                brand_name=brand_name,
                model_name=model_name,
            )
            if looked_up and await validate_image_url(looked_up, client=client):
                return looked_up

    return None
