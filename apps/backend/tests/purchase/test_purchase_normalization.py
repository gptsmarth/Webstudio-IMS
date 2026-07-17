"""Deterministic model-number normalization unit tests (Purchase Import only)."""

from __future__ import annotations

import pytest

from webstudio_backend.integrations.tally.purchase_normalization import (
    ACCESSORY_AUTO_SELECT_SCORE,
    ACCESSORY_SUGGEST_SCORE,
    accessory_match_score,
    models_match,
    models_partial_match,
    normalize_model_number,
)


@pytest.mark.parametrize(
    ("raw", "brand", "short", "expected"),
    [
        ("ASUS F1504FA-BQ2113WS", "ASUS", None, "F1504FA-BQ2113WS"),
        ("HP 15-FD0456TU", "HP", None, "15-FD0456TU"),
        ("LENOVO 82XQ00W4IN", "Lenovo", None, "82XQ00W4IN"),
        # Already clean — brand not present as a prefix.
        ("F1504FA-BQ2113WS", "ASUS", None, "F1504FA-BQ2113WS"),
        # Collapse + trim + uppercase.
        ("  asus   f1504fa-bq2113ws  ", "ASUS", None, "F1504FA-BQ2113WS"),
        # No brand prefix present on an accessory name.
        ("Carry Case", "ASUS", None, "CARRY CASE"),
        # Short-name prefix stripping.
        ("LN 82XQ00W4IN", "Lenovo", "LN", "82XQ00W4IN"),
    ],
)
def test_normalize_examples(raw: str, brand: str, short: str | None, expected: str) -> None:
    assert normalize_model_number(raw, brand_name=brand, brand_short_name=short) == expected


def test_no_partial_prefix_strip() -> None:
    # "HP" must not strip the "HP" inside a token with no word boundary.
    assert normalize_model_number("HPX123", brand_name="HP") == "HPX123"


def test_prefix_equal_to_value_is_kept() -> None:
    assert normalize_model_number("ASUS", brand_name="ASUS") == "ASUS"


def test_empty_returns_empty() -> None:
    assert normalize_model_number("   ", brand_name="ASUS") == ""


def test_models_match_is_exact_after_normalization() -> None:
    assert models_match("ASUS F1504FA-BQ2113WS", "F1504FA-BQ2113WS", brand_name="ASUS")
    assert not models_match("ASUS F1504FA-BQ2113WS", "F1504FA-BQ9999WS", brand_name="ASUS")


def test_models_match_empty_is_false() -> None:
    assert not models_match("", "F1504FA-BQ2113WS", brand_name="ASUS")


# --- Partial ("somewhere in between") model matching --------------------------


def test_partial_match_ims_has_base_model_suffix() -> None:
    # The reported case: Tally bill "S3407QA-KP027WS" vs IMS catalogue entry
    # "S3407QA-KP027WS(S3407QA)". The bill value is contained in the IMS value.
    assert models_partial_match(
        "S3407QA-KP027WS",
        "S3407QA-KP027WS(S3407QA)",
        brand_name="ASUS",
    )


def test_partial_match_is_symmetric() -> None:
    assert models_partial_match(
        "S3407QA-KP027WS(S3407QA)",
        "S3407QA-KP027WS",
        brand_name="ASUS",
    )


def test_partial_match_exact_is_not_partial() -> None:
    # Exact matches are reported by models_match, never as a partial suggestion.
    assert not models_partial_match(
        "ASUS F1504FA-BQ2113WS",
        "F1504FA-BQ2113WS",
        brand_name="ASUS",
    )


def test_partial_match_unrelated_is_false() -> None:
    assert not models_partial_match(
        "F1504FA-BQ2113WS",
        "82XQ00W4IN",
        brand_name="ASUS",
    )


def test_partial_match_short_fragment_guarded() -> None:
    # A tiny shared fragment must not trigger a partial match.
    assert not models_partial_match("15", "15-FD0456TU", brand_name="HP")


def test_partial_match_empty_is_false() -> None:
    assert not models_partial_match("", "S3407QA-KP027WS", brand_name="ASUS")


# --- Accessory fuzzy matching -------------------------------------------------


def test_accessory_exact_after_brand_strip() -> None:
    # Tally "MD102" vs catalogue model_number "MD102" (brand stripped) -> exact.
    score = accessory_match_score(
        "MD102",
        candidate_model_number="MD102",
        candidate_model_name="ASUS MD102 mouse",
        brand_name="ASUS",
    )
    assert score == 1.0


def test_accessory_extra_descriptor_still_matches() -> None:
    # Tally "ASUS MD102 SILENT" vs catalogue "MD102" -> whole-token match.
    score = accessory_match_score(
        "ASUS MD102 SILENT",
        candidate_model_number="MD102",
        brand_name="ASUS",
    )
    assert score >= ACCESSORY_AUTO_SELECT_SCORE


def test_accessory_part_number_with_punctuation() -> None:
    # Part number "MD-102" should match the "MD102" token in the Tally name.
    score = accessory_match_score(
        "ASUS MD102 SILENT",
        candidate_model_number="OTHER",
        candidate_part_number="MD-102",
        brand_name="ASUS",
    )
    assert score >= ACCESSORY_AUTO_SELECT_SCORE


def test_accessory_unrelated_scores_low() -> None:
    score = accessory_match_score(
        "ASUS MD102 SILENT",
        candidate_model_number="ZX900",
        candidate_model_name="ASUS ZX900 keyboard",
        brand_name="ASUS",
    )
    assert score < ACCESSORY_SUGGEST_SCORE


def test_accessory_name_only_rough_match() -> None:
    score = accessory_match_score(
        "ASUS SILENT MOUSE",
        candidate_model_number="MD102",
        candidate_model_name="ASUS Silent Mouse",
        brand_name="ASUS",
    )
    assert score >= ACCESSORY_SUGGEST_SCORE


def test_accessory_empty_query_is_zero() -> None:
    assert accessory_match_score("", candidate_model_number="MD102") == 0.0
