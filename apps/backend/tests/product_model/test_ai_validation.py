"""Tests for strict AI enrichment validation."""

from webstudio_backend.services.ai.spec_normalization import (
    product_line_matches_sku,
    validate_enrichment_payload,
)


def test_groq_hallucination_fa506ncq_vivobook_rejected() -> None:
    """Groq guessed Vivobook specs for a TUF Gaming FA506 SKU — must be rejected."""
    payload = {
        "model_name": "ASUS Vivobook 14 FA506NCQ",
        "cpu": "Intel Core i5-1235U",
        "gpu": "NVIDIA GeForce MX570",
        "ram_gb": 16,
        "storage_value": "512",
        "storage_unit": "GB",
        "storage_type": "SSD",
        "description": (
            "The ASUS Vivobook 14 FA506NCQ is a compact and powerful laptop designed for everyday use."
        ),
        "notes": "Based on general ASUS listing",
        "confidence_score": 0.90,
        "source": "groq",
    }
    assert product_line_matches_sku("FA506NCQ-HN006W", payload, brand_name="ASUS") is False
    assert validate_enrichment_payload(
        payload,
        model_number="FA506NCQ-HN006W",
        provider="groq",
        brand_name="ASUS",
    ) is False


def test_groq_requires_full_sku_citation() -> None:
    payload = {
        "model_name": "ASUS TUF Gaming A15 FA506NCQ",
        "cpu": "AMD Ryzen 7 7435HS",
        "gpu": "NVIDIA GeForce RTX 2050",
        "ram_gb": 16,
        "storage_value": "512",
        "storage_unit": "GB",
        "storage_type": "SSD",
        "notes": "Matched retailer listing for FA506NCQ-HN006W",
        "confidence_score": 0.96,
        "source": "groq",
    }
    assert validate_enrichment_payload(
        payload,
        model_number="FA506NCQ-HN006W",
        provider="groq",
        brand_name="ASUS",
    ) is True


def test_gemini_allows_family_anchor_with_grounding() -> None:
    payload = {
        "model_name": "ASUS TUF Gaming A14",
        "cpu": "AMD Ryzen AI 9 HX 370",
        "ram_gb": 32,
        "storage_value": "1",
        "storage_unit": "TB",
        "storage_type": "SSD",
        "notes": "Matched official listing for FA401EA-RG020WS",
        "confidence_score": 0.88,
        "source": "gemini",
    }
    assert validate_enrichment_payload(
        payload,
        model_number="FA401EA-RG020WS",
        provider="gemini",
        brand_name="ASUS",
    ) is True
