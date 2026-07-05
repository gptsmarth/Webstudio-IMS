"""Tests for Tally GST amount helpers."""

from __future__ import annotations

from webstudio_backend.integrations.tally.gst import split_sale_amount_with_gst


def test_split_sale_amount_with_gst_applies_eighteen_percent() -> None:
    exclusive, inclusive = split_sale_amount_with_gst(125000.0)
    assert exclusive == 125000.0
    assert inclusive == 147500.0


def test_split_sale_amount_with_gst_none() -> None:
    assert split_sale_amount_with_gst(None) == (None, None)
