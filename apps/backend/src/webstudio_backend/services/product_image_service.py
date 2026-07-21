"""Resolve and validate laptop product image URLs from the public web."""

from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
MAX_PAGE_FETCHES = 4
MAX_CANDIDATES = 12
_SUSPICIOUS_IMAGE_URL_PATTERNS = (
    re.compile(r"88888888-8888-8888-8888-888888888888", re.IGNORECASE),
    re.compile(r"00000000-0000-0000-0000-000000000000", re.IGNORECASE),
    re.compile(r"placeholder", re.IGNORECASE),
    re.compile(r"no[_-]?image", re.IGNORECASE),
)


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


def is_suspicious_placeholder_image_url(url: str) -> bool:
    """Reject common LLM-hallucinated or template image URLs."""
    lowered = url.lower()
    if any(pattern.search(lowered) for pattern in _SUSPICIOUS_IMAGE_URL_PATTERNS):
        return True
    host = (urlparse(lowered).hostname or "").lower()
    return host in {"example.com", "www.example.com", "example.org", "example.net"}


# Real product photos are never this small; 8x8 tracking pixels and tiny
# icons slip past content-type checks because they are valid JPEG/PNG files.
MIN_PRODUCT_IMAGE_DIMENSION = 96


def image_bytes_too_small(content: bytes) -> bool:
    """True when the bytes decode to an image smaller than a usable product photo.

    Returns False when the bytes cannot be decoded (partial download or an
    unsupported format like AVIF) — only a confirmed tiny image is rejected.
    """
    import io

    from PIL import Image

    try:
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
    except Exception:
        return False
    return min(width, height) < MIN_PRODUCT_IMAGE_DIMENSION


MAX_PRODUCT_IMAGE_ASPECT_RATIO = 2.5


def image_has_extreme_aspect_ratio(content: bytes) -> bool:
    """Reject wide banners / port logos (e.g. HDMI badges) that are not product photos."""
    import io

    from PIL import Image

    try:
        with Image.open(io.BytesIO(content)) as img:
            width, height = img.size
    except Exception:
        return False
    if width <= 0 or height <= 0:
        return True
    ratio = max(width, height) / min(width, height)
    return ratio > MAX_PRODUCT_IMAGE_ASPECT_RATIO


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
        if is_suspicious_placeholder_image_url(url):
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


def extract_image_urls_from_html(
    html: str,
    page_url: str,
    *,
    include_all_images: bool = False,
) -> list[str]:
    urls: list[str] = []
    patterns = (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<meta[^>]+itemprop=["\']image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+itemprop=["\']image["\']',
        r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']',
        r'"image"\s*:\s*\[?["\'](https://[^"\']+\.(?:jpg|jpeg|png|webp))["\']',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            urls.append(match.group(1).strip())

    img_attr_patterns = (
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+data-src=["\']([^"\']+)["\']',
        r'<img[^>]+data-lazy-src=["\']([^"\']+)["\']',
    )
    for pattern in img_attr_patterns:
        for match in re.finditer(pattern, html, flags=re.IGNORECASE):
            src = match.group(1).strip()
            lowered = src.lower()
            if include_all_images or any(
                token in lowered for token in ("product", "laptop", "notebook", "hero", "gallery")
            ):
                urls.append(src)

    for match in re.finditer(
        r'srcset=["\']([^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    ):
        for part in match.group(1).split(","):
            candidate = part.strip().split(" ", 1)[0].strip()
            if candidate:
                urls.append(candidate)

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


def _content_looks_like_image(content: bytes, content_type: str) -> bool:
    if content_type in IMAGE_CONTENT_TYPES:
        return True
    if content.startswith(b"\xff\xd8\xff"):
        return True
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True
    return False


UPLOAD_ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp"})
UPLOAD_ALLOWED_MIME_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp"},
)
_UPLOAD_MIME_TO_FORMAT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _extension_from_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        return "jpg"
    if ext == ".jpg":
        return "jpg"
    if ext == ".png":
        return "png"
    if ext == ".webp":
        return "webp"
    return None


def detect_upload_image_format(payload: bytes) -> str | None:
    if payload.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "webp"
    return None


def _verify_image_decodable(payload: bytes) -> None:
    from io import BytesIO

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(BytesIO(payload)) as image:
            image.verify()
        with Image.open(BytesIO(payload)) as image:
            image.load()
    except (UnidentifiedImageError, OSError, SyntaxError) as exc:
        raise ValueError("Uploaded file is not a valid image.") from exc


def validate_product_image_upload(
    *,
    filename: str | None,
    content_type: str | None,
    payload: bytes,
) -> str:
    """Validate an uploaded product image and return the normalized file extension."""
    if not payload:
        raise ValueError("Uploaded file is empty.")

    extension_format = _extension_from_filename(filename)
    if extension_format is None:
        raise ValueError("Unsupported file extension. Allowed: JPG, JPEG, PNG, WEBP.")

    raw_filename = (filename or "").strip()
    if raw_filename and Path(raw_filename).suffix.lower() not in UPLOAD_ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file extension. Allowed: JPG, JPEG, PNG, WEBP.")

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in UPLOAD_ALLOWED_MIME_TYPES:
        raise ValueError("Unsupported content type. Allowed: JPEG, PNG, WEBP.")

    mime_format = _UPLOAD_MIME_TO_FORMAT.get(mime)
    if mime_format is None or mime_format != extension_format:
        raise ValueError("File extension and content type do not match.")

    magic_format = detect_upload_image_format(payload)
    if magic_format is None:
        raise ValueError("File signature is not a supported image format.")

    if magic_format != extension_format:
        raise ValueError("File signature does not match the declared image type.")

    if payload[:2] == b"MZ" or payload[:4] == b"\x7fELF":
        raise ValueError("Executable files are not allowed.")

    _verify_image_decodable(payload)
    return magic_format


async def validate_image_url(url: str, *, client: httpx.AsyncClient | None = None) -> bool:
    normalized = _normalize_https_url(url)
    if not normalized or not is_safe_public_https_url(normalized):
        return False
    if is_suspicious_placeholder_image_url(normalized):
        return False

    owns_client = client is None
    http = client or httpx.AsyncClient(
        timeout=12.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )
    try:
        response = await http.get(
            normalized,
            headers={"Range": "bytes=0-8191", "User-Agent": USER_AGENT},
        )
        if response.status_code not in {200, 206}:
            return False
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if _content_looks_like_image(response.content[:16], content_type):
            # Image headers (with dimensions) sit in the first bytes, so the
            # ranged download is enough to reject tracking pixels and icons.
            return not image_bytes_too_small(response.content)
        return _looks_like_image_url(normalized) and bool(response.content)
    except httpx.HTTPError:
        return False
    finally:
        if owns_client:
            await http.aclose()


async def fetch_page_html(url: str, *, client: httpx.AsyncClient) -> str | None:
    if not is_safe_public_https_url(url):
        return None
    browser_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    try:
        response = await client.get(
            url,
            headers={
                "User-Agent": browser_ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if response.status_code >= 400:
            return None
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type and "text/" not in content_type:
            return None
        return response.text
    except httpx.HTTPError as exc:
        logger.debug("Product page fetch failed for {}: {}", url, type(exc).__name__)
        return None


async def search_public_web_for_pages(query: str, *, client: httpx.AsyncClient) -> list[str]:
    urls: list[str] = []
    try:
        resp = await client.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT, "Referer": "https://html.duckduckgo.com/"},
        )
        if resp.status_code == 200:
            for match in re.finditer(
                r'class="result__url"\s+href="([^"]+)"', resp.text, flags=re.IGNORECASE
            ):
                url = match.group(1).strip()
                if url.startswith("//"):
                    url = f"https:{url}"
                if is_safe_public_https_url(url):
                    urls.append(url)
            if not urls:
                for match in re.finditer(
                    r'href="(https://[^"]+(?:asus|hp|lenovo|dell|acer|apple|samsung|amazon|flipkart|msi|croma|reliancedigital|vijaysales)[^"]*)"',
                    resp.text,
                    flags=re.IGNORECASE,
                ):
                    url = match.group(1).strip()
                    if is_safe_public_https_url(url):
                        urls.append(url)
    except Exception as exc:
        logger.debug("Public web search failed for query '{}': {}", query, type(exc).__name__)
    return _dedupe_urls(urls)[:4]


async def resolve_product_image(
    *,
    model_number: str,
    brand_name: str | None = None,
    model_name: str | None = None,
    candidate_url: str | None = None,
    grounding_body: dict[str, Any] | None = None,
    model_id: str | None = None,
    persist_local: bool = False,
    image_search_query: str | None = None,
    fast: bool = False,
    max_queries: int | None = None,
) -> str | None:
    """Find a loadable product image using free web scraping (DuckDuckGo + page HTML)."""

    candidates: list[str] = []
    if candidate_url:
        candidates.append(candidate_url)

    for page_url in extract_grounding_page_urls(grounding_body):
        if _looks_like_image_url(page_url):
            candidates.append(page_url)

    page_fetch_limit = 0 if fast else MAX_PAGE_FETCHES
    if page_fetch_limit:
        async with httpx.AsyncClient(
            timeout=15.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            for page_url in extract_grounding_page_urls(grounding_body)[:page_fetch_limit]:
                if _looks_like_image_url(page_url):
                    continue
                html = await fetch_page_html(page_url, client=client)
                if html:
                    candidates.extend(extract_image_urls_from_html(html, page_url))

    from webstudio_backend.services.web_image_scraper import discover_product_image_url

    image_search_queries = [image_search_query] if image_search_query else None
    return await discover_product_image_url(
        model_number=model_number,
        brand_name=brand_name,
        model_name=model_name,
        candidate_urls=_dedupe_urls(candidates),
        model_id=model_id,
        persist_local=persist_local,
        image_search_queries=image_search_queries,
        max_queries=max_queries if max_queries is not None else (2 if fast else None),
    )
