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
