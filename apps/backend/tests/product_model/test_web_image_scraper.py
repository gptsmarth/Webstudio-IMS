"""Tests for free web image scraper."""

from webstudio_backend.services.web_image_scraper import (
    build_brand_direct_image_candidates,
    build_product_image_search_queries,
    score_image_candidate_url,
)


def test_build_product_image_search_queries() -> None:
    queries = build_product_image_search_queries(
        "X1502ZA-EJ541WS",
        brand_name="ASUS",
        model_name="Vivobook 15",
    )
    assert any("X1502ZA-EJ541WS" in query for query in queries)
    assert any("ASUS" in query for query in queries)
    assert any("site:asus.com" in query for query in queries)
    assert any("site:amazon.in" in query for query in queries)


def test_build_brand_direct_image_candidates_asus() -> None:
    urls = build_brand_direct_image_candidates("FA506NCQ-HN006W", brand_name="ASUS")
    assert urls[0].startswith("https://in.store.asus.com/media/catalog/product/")


def test_score_image_candidate_url_prefers_manufacturer_cdn() -> None:
    asus = "https://dlcdnwebimgs.asus.com/pub/ASUS/notebook/X1502ZA.jpg"
    random = "https://cdn.random-cdn.net/thumb/icon.png"
    assert score_image_candidate_url(
        asus, brand_name="ASUS", model_number="X1502ZA"
    ) > score_image_candidate_url(
        random,
        brand_name="ASUS",
        model_number="X1502ZA",
    )


def test_amazon_cdn_without_sku_is_not_relevant() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    amazon_bookish = "https://m.media-amazon.com/images/I/81XDTbkpMpL._AC_SL1500_.jpg"
    assert not is_relevant_product_image(
        amazon_bookish,
        "X1504VA-BQ342WS",
        brand_name="ASUS",
    )


def test_amazon_cdn_allowed_when_page_mentions_sku() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    amazon = "https://m.media-amazon.com/images/I/81XDTbkpMpL._AC_SL1500_.jpg"
    assert is_relevant_product_image(
        amazon,
        "X1504VA-BQ342WS",
        brand_name="ASUS",
        page_mentions_sku=True,
    )


def test_manufacturer_url_with_sku_is_relevant() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    asus = "https://dlcdnwebimgs.asus.com/pub/ASUS/nb/X1504VA-BQ342WS/hero.jpg"
    assert is_relevant_product_image(asus, "X1504VA-BQ342WS", brand_name="ASUS")


def test_book_path_fragments_are_blocked() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    book = "https://dlcdnwebimgs.asus.com/media/books/cover.jpg"
    assert not is_relevant_product_image(book, "X1504VA-BQ342WS", brand_name="ASUS")
    notebook = "https://dlcdnwebimgs.asus.com/pub/ASUS/notebook/X1504VA.jpg"
    assert is_relevant_product_image(notebook, "X1504VA-BQ342WS", brand_name="ASUS")


def test_manufacturer_url_without_sku_requires_page_context() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    generic = "https://dlcdnwebimgs.asus.com/pub/ASUS/notebook/generic-hero.jpg"
    assert not is_relevant_product_image(generic, "UX3405CA-QL1014WS", brand_name="ASUS")
    assert is_relevant_product_image(
        generic,
        "UX3405CA-QL1014WS",
        brand_name="ASUS",
        page_mentions_sku=True,
    )


def test_hdmi_feature_path_is_blocked() -> None:
    from webstudio_backend.services.web_image_scraper import is_relevant_product_image

    hdmi = "https://dlcdnwebimgs.asus.com/pub/ASUS/notebook/hdmi-logo.jpg"
    assert not is_relevant_product_image(hdmi, "UX3405CA-QL1014WS", brand_name="ASUS")


def test_image_has_extreme_aspect_ratio_rejects_banners() -> None:
    import io

    from PIL import Image

    from webstudio_backend.services.product_image_service import image_has_extreme_aspect_ratio

    banner = io.BytesIO()
    Image.new("RGB", (800, 120)).save(banner, format="JPEG")
    assert image_has_extreme_aspect_ratio(banner.getvalue()) is True

    product = io.BytesIO()
    Image.new("RGB", (800, 600)).save(product, format="JPEG")
    assert image_has_extreme_aspect_ratio(product.getvalue()) is False


def test_image_bytes_too_small_rejects_tracking_pixels() -> None:
    import io

    from PIL import Image

    from webstudio_backend.services.product_image_service import image_bytes_too_small

    tiny = io.BytesIO()
    Image.new("RGB", (8, 8)).save(tiny, format="JPEG")
    assert image_bytes_too_small(tiny.getvalue()) is True

    real = io.BytesIO()
    Image.new("RGB", (400, 300)).save(real, format="JPEG")
    assert image_bytes_too_small(real.getvalue()) is False

    # Undecodable bytes (e.g. truncated/AVIF) must not be rejected.
    assert image_bytes_too_small(b"\x00\x01\x02") is False
