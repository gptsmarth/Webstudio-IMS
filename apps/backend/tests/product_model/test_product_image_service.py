"""Tests for product image resolution helpers."""

from webstudio_backend.services.product_image_service import (
    _content_looks_like_image,
    _dedupe_urls,
    extract_grounding_page_urls,
    extract_image_urls_from_html,
    is_safe_public_https_url,
    is_suspicious_placeholder_image_url,
)


def test_is_safe_public_https_url_rejects_localhost() -> None:
    assert is_safe_public_https_url("https://example.com/image.jpg") is True
    assert is_safe_public_https_url("http://example.com/image.jpg") is False
    assert is_safe_public_https_url("https://localhost/image.jpg") is False


def test_extract_grounding_page_urls() -> None:
    body = {
        "candidates": [
            {
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"uri": "https://www.asus.com/laptops/example"}},
                        {"web": {"uri": "https://dlcdnets.asus.com/pub/ASUS/notebook/image.jpg"}},
                    ]
                }
            }
        ]
    }
    urls = extract_grounding_page_urls(body)
    assert "https://www.asus.com/laptops/example" in urls
    assert "https://dlcdnets.asus.com/pub/ASUS/notebook/image.jpg" in urls


def test_extract_image_urls_from_html_finds_og_image() -> None:
    html = """
    <html><head>
      <meta property="og:image" content="https://cdn.example.com/hero.png" />
    </head></html>
  """
    urls = extract_image_urls_from_html(html, "https://www.example.com/product")
    assert urls == ["https://cdn.example.com/hero.png"]


def test_dedupe_urls_normalizes_protocol_relative() -> None:
    urls = _dedupe_urls(["//cdn.example.com/a.jpg", "https://cdn.example.com/a.jpg"])
    assert urls == ["https://cdn.example.com/a.jpg"]


def test_is_suspicious_placeholder_image_url_rejects_hallucinated_asus_cdn() -> None:
    fake = "https://dlcdnwebimgs.asus.com/gain/" "88888888-8888-8888-8888-888888888888/w800/h600"
    assert is_suspicious_placeholder_image_url(fake) is True
    assert is_suspicious_placeholder_image_url("https://cdn.asus.com/real-product.jpg") is False


def test_dedupe_urls_skips_placeholder_images() -> None:
    fake = "https://dlcdnwebimgs.asus.com/gain/" "88888888-8888-8888-8888-888888888888/w800/h600"
    real = "https://cdn.asus.com/laptop.jpg"
    assert _dedupe_urls([fake, real]) == [real]


def test_content_looks_like_image_detects_jpeg_magic_bytes() -> None:
    assert _content_looks_like_image(b"\xff\xd8\xff\xe0", "application/octet-stream") is True
    assert _content_looks_like_image(b"<html>", "text/html") is False
