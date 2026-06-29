"""Tests for free web image scraper."""

from webstudio_backend.services.web_image_scraper import (
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


def test_score_image_candidate_url_prefers_manufacturer_cdn() -> None:
    from webstudio_backend.services.web_image_scraper import score_image_candidate_url

    asus = "https://dlcdnwebimgs.asus.com/pub/ASUS/notebook/X1502ZA.jpg"
    random = "https://cdn.random-cdn.net/thumb/icon.png"
    assert score_image_candidate_url(asus, brand_name="ASUS", model_number="X1502ZA") > score_image_candidate_url(
        random,
        brand_name="ASUS",
        model_number="X1502ZA",
    )
