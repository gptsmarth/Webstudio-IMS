"""Tests for Gemini laptop spec lookup."""

from webstudio_backend.services.gemini_spec_service import (
    _normalize_cpu,
    _normalize_spec,
    _parse_json_object,
)


def test_normalize_spec_maps_fields() -> None:
    result = _normalize_spec(
        {
            "model_name": "Vivobook 15",
            "cpu": "Intel Core i5-1335U",
            "gpu": "Intel UHD",
            "ram_gb": "16",
            "storage_value": 512,
            "storage_unit": "gb",
            "storage_type": "ssd",
            "display": '15.6" FHD IPS 60Hz',
            "color_options": "Quiet Blue, Cool Silver",
            "operating_system": "Windows 11 Home",
            "battery": "42 Wh",
            "weight": "1.7 kg",
            "connectivity": "Wi-Fi 6, Bluetooth 5.2",
            "product_image_url": "https://example.com/laptop.jpg",
            "notes": "Matched official ASUS India listing",
        },
        fallback_name="X151VA",
    )

    assert result["model_name"] == "Vivobook 15"
    assert result["cpu"] == "Intel Core i5-1335U"
    assert result["ram_gb"] == 16
    assert result["storage_unit"] == "GB"
    assert result["storage_type"] == "SSD"
    assert result["color_options"] == "Quiet Blue, Cool Silver"
    assert "Operating system: Windows 11 Home" in result["notes"]
    assert "Matched official ASUS India listing" in result["notes"]
    assert result["product_image_url"] == "https://example.com/laptop.jpg"
    assert result["source"] == "gemini"


def test_normalize_spec_rejects_non_https_image() -> None:
    result = _normalize_spec(
        {"cpu": "AMD Ryzen 5", "product_image_url": "http://insecure.example/x.jpg"},
        fallback_name="Model",
    )
    assert result["product_image_url"] is None


def test_parse_json_object_extracts_embedded_object() -> None:
    parsed = _parse_json_object('Here is the data: {"cpu": "Intel", "ram_gb": 8}')
    assert parsed == {"cpu": "Intel", "ram_gb": 8}


def test_normalize_cpu_extracts_chip_name() -> None:
    assert _normalize_cpu("Intel® Core™ i5-1335U Processor 1.2 GHz (10MB Cache)") == "Intel Core i5-1335U"

