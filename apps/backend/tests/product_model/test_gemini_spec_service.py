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
            "product_image_url": "https://cdn.asus.com/media/laptop.jpg",
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
    assert result["product_image_url"] == "https://cdn.asus.com/media/laptop.jpg"
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
    assert (
        _normalize_cpu("Intel® Core™ i5-1335U Processor 1.2 GHz (10MB Cache)")
        == "Intel Core i5-1335U"
    )


def test_normalize_spec_does_not_invent_ram_or_storage() -> None:
    result = _normalize_spec(
        {"cpu": "Intel Core i5-1335U", "model_name": "X1502ZA-EJ541WS"}, fallback_name="X1502ZA"
    )
    assert result["ram_gb"] is None
    assert result["storage_value"] == ""


def test_response_anchors_model_number() -> None:
    from webstudio_backend.services.gemini_spec_service import _response_anchors_model_number

    anchored = {
        "model_name": "ASUS TUF Gaming A14",
        "notes": "Matched official listing for FA401EA-RG020WS",
        "description": "Portable gaming laptop.",
    }
    wrong = {
        "model_name": "Vivobook 15",
        "notes": "Generic ASUS listing",
        "description": "Everyday laptop.",
    }
    assert _response_anchors_model_number("FA401EA-RG020WS", anchored) is True
    assert _response_anchors_model_number("FA401EA-RG020WS", wrong) is False
