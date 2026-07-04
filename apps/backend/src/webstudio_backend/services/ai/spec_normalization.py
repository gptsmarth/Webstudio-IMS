"""Normalize and validate AI enrichment payloads."""

from __future__ import annotations

import re
from typing import Any


def normalize_cpu(cpu: str) -> str:
    cleaned = cpu.replace("®", "").replace("™", "").strip()
    match = re.search(
        r"((?:Intel|AMD)\s+(?:Core|Ryzen)\s+[A-Za-z0-9\s\-]+?)(?:\s+Processor|\s+\d+\.?\d*\s*GHz|\s*\(|,|$)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return cleaned[:128]


def normalize_gpu(gpu: Any) -> str | None:
    if gpu is None:
        return None
    value = str(gpu).strip()
    if not value or value.lower() in {"null", "none", "n/a"}:
        return None
    value = value.replace("®", "").replace("™", "").strip()
    if re.search(r"integrated", value, re.IGNORECASE):
        uhd = re.search(r"(Intel\s+UHD\s+Graphics[^,\(]*)", value, re.IGNORECASE)
        if uhd:
            return re.sub(r"\s+", " ", uhd.group(1)).strip()
        radeon = re.search(r"(AMD\s+Radeon\s+Graphics)", value, re.IGNORECASE)
        if radeon:
            return radeon.group(1)
    return value[:128]


def normalize_color_options(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    return text[:256]


def compose_spec_notes(data: dict[str, Any]) -> str | None:
    spec_lines: list[str] = []
    for key, label in (
        ("operating_system", "Operating system"),
        ("memory_type", "Memory type"),
        ("battery", "Battery"),
        ("weight", "Weight"),
        ("connectivity", "Connectivity"),
        ("keyboard", "Keyboard"),
        ("webcam", "Webcam"),
        ("audio", "Audio"),
        ("charger", "Charger"),
        ("warranty", "Warranty"),
    ):
        raw = data.get(key)
        if raw is None:
            continue
        value = str(raw).strip()
        if not value or value.lower() in {"null", "none", "n/a"}:
            continue
        spec_lines.append(f"{label}: {value}")

    source = data.get("notes")
    source_str = str(source).strip() if source else ""
    if spec_lines and source_str:
        return "\n".join(spec_lines) + "\n---\n" + source_str
    if spec_lines:
        return "\n".join(spec_lines)
    return source_str or None


def response_anchors_model_number(
    model_number: str,
    result: dict[str, Any],
    *,
    strict: bool = False,
) -> bool:
    """Reject guesses that never mention the searched SKU or its family prefix."""
    sku = model_number.strip().upper()
    if not sku:
        return False
    haystack = " ".join(
        str(result.get(key) or "") for key in ("model_name", "notes", "description")
    ).upper()
    if sku in haystack:
        return True
    if strict:
        return False
    family = sku.split("-", 1)[0]
    if len(family) >= 4 and family in haystack:
        return True
    return sku in str(result.get("model_name") or "").upper()


_ASUS_GAMING_FAMILY = re.compile(r"^(FA[567]|FX[567]|GU|GA|G[567]|RC7)", re.IGNORECASE)
_ASUS_CONSUMER_FAMILY = re.compile(r"^(X|E|M|S|UX|K\d|D\d)", re.IGNORECASE)
_CONSUMER_LINE_MARKERS = ("vivobook", "zenbook", "chromebook", "expertbook")
_GAMING_LINE_MARKERS = (
    "tuf gaming",
    "tuf ",
    "rog ",
    "republic of gamers",
    "strix",
    "zephyrus",
    "tuf-a",
)


def product_line_matches_sku(
    model_number: str,
    result: dict[str, Any],
    *,
    brand_name: str | None = None,
) -> bool:
    """Reject obvious product-line hallucinations (e.g. FA506 TUF SKU labeled Vivobook)."""
    brand = (brand_name or "").strip().lower()
    if brand and brand != "asus":
        return True

    family = model_number.strip().upper().split("-", 1)[0]
    text = " ".join(
        str(result.get(key) or "") for key in ("model_name", "description", "notes")
    ).lower()

    if _ASUS_GAMING_FAMILY.match(family):
        if any(marker in text for marker in _CONSUMER_LINE_MARKERS):
            return False
    if _ASUS_CONSUMER_FAMILY.match(family):
        if any(marker in text for marker in _GAMING_LINE_MARKERS):
            return False
    return True


_UNGROUNDED_PROVIDERS = frozenset({"openai", "groq", "openrouter"})


def validate_enrichment_payload(
    normalized: dict[str, Any],
    *,
    model_number: str,
    provider: str = "gemini",
    brand_name: str | None = None,
) -> bool:
    if not normalized.get("cpu"):
        return False
    if normalized.get("ram_gb") is None:
        return False
    if not normalized.get("storage_value"):
        return False
    strict = provider in _UNGROUNDED_PROVIDERS
    if not response_anchors_model_number(model_number, normalized, strict=strict):
        return False
    if not product_line_matches_sku(model_number, normalized, brand_name=brand_name):
        return False
    if strict:
        confidence = float(normalized.get("confidence_score") or 0.0)
        if confidence < 0.95:
            return False
    return True


def normalize_spec(
    data: dict[str, Any], fallback_name: str, *, source: str = "gemini"
) -> dict[str, Any]:
    storage_unit = str(data.get("storage_unit", "GB")).upper()
    if storage_unit not in {"GB", "TB"}:
        storage_unit = "GB"
    storage_type = str(data.get("storage_type", "SSD")).upper()
    if storage_type not in {"SSD", "HDD"}:
        storage_type = "SSD"

    ram = data.get("ram_gb")
    try:
        ram_gb = int(ram) if ram is not None and str(ram).strip() else None
    except (TypeError, ValueError):
        ram_gb = None

    storage_raw = data.get("storage_value")
    storage_value = (
        str(storage_raw).strip() if storage_raw is not None and str(storage_raw).strip() else None
    )

    image_url = data.get("product_image_url")
    if image_url is not None:
        from webstudio_backend.services.product_image_service import (
            _normalize_https_url,
            is_suspicious_placeholder_image_url,
        )

        normalized = _normalize_https_url(str(image_url))
        if not normalized or is_suspicious_placeholder_image_url(normalized):
            image_url = None
        else:
            image_url = normalized

    notes = data.get("notes")
    spec_keys = (
        "operating_system",
        "memory_type",
        "battery",
        "weight",
        "connectivity",
        "keyboard",
        "webcam",
        "audio",
        "charger",
        "warranty",
        "notes",
    )
    notes_str = (
        compose_spec_notes(data)
        if any(data.get(key) for key in spec_keys)
        else (str(notes).strip() if notes else None)
    )

    description_raw = data.get("description")
    description = str(description_raw).strip() if description_raw else None
    if description and description.lower() in {"null", "none", "n/a"}:
        description = None

    confidence_raw = data.get("confidence_score")
    try:
        confidence_score = float(confidence_raw) if confidence_raw is not None else 0.75
    except (TypeError, ValueError):
        confidence_score = 0.75
    confidence_score = max(0.0, min(1.0, confidence_score))

    return {
        "model_name": str(data.get("model_name") or fallback_name).strip(),
        "cpu": normalize_cpu(str(data.get("cpu") or "")),
        "gpu": normalize_gpu(data.get("gpu")),
        "ram_gb": ram_gb,
        "storage_value": storage_value or "",
        "storage_unit": storage_unit,
        "storage_type": storage_type,
        "display": (str(data.get("display")).strip() or None) if data.get("display") else None,
        "color_options": normalize_color_options(data.get("color_options")),
        "product_image_url": image_url,
        "description": description,
        "notes": notes_str,
        "source": source,
        "confidence_score": confidence_score,
    }


def normalize_model_number(model_number: str) -> str:
    return model_number.strip().upper()


def normalize_brand_name(brand_name: str | None) -> str | None:
    if not brand_name:
        return None
    cleaned = brand_name.strip()
    return cleaned or None
