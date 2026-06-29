"""Gemini LLM laptop specification lookup."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from loguru import logger

from webstudio_backend.core.config import Settings

# Grounded web search — matches Gemini chat accuracy. Avoid flash-lite without search.
DEFAULT_MODEL = "gemini-2.5-flash"
GROUNDED_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
)


class GeminiLookupError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class GeminiSpecService:
    def __init__(self, settings: Settings | None = None, *, api_key: str | None = None, model: str | None = None) -> None:
        env_key = settings.gemini_api_key.strip() if settings else ""
        env_model = settings.gemini_model.strip() if settings else ""
        self._api_key = (api_key or env_key).strip()
        self._model = (model or env_model or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _grounded_model_chain(self) -> list[str]:
        chain: list[str] = []
        for candidate in (self._model, *GROUNDED_MODELS):
            name = candidate.strip()
            if name and name not in chain:
                chain.append(name)
        return chain

    async def lookup_laptop_spec(
        self,
        model_number: str,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_configured:
            raise GeminiLookupError(
                "SERVICE_UNAVAILABLE",
                "Gemini API is not configured. Add your API key in System Settings → Integrations.",
            )

        model_number = model_number.strip()
        if not model_number:
            raise GeminiLookupError("NOT_FOUND", "Model number is required.")

        prompt = _build_lookup_prompt(model_number, brand_name=brand_name, model_name=model_name)
        rate_limited_models: list[str] = []
        last_error: GeminiLookupError | None = None

        for gemini_model in self._grounded_model_chain():
            try:
                payload = _build_payload(prompt, use_grounding=True)
                body = await self._generate(gemini_model, payload)
                result = _parse_lookup_response(
                    body,
                    fallback_name=model_name or model_number,
                    model_number=model_number,
                )
                if result:
                    if gemini_model != self._model:
                        logger.info("Gemini grounded lookup succeeded via {}", gemini_model)
                    return await self._finalize_lookup_result(
                        result,
                        body=body,
                        model_number=model_number,
                        brand_name=brand_name,
                        model_name=model_name,
                    )
            except GeminiLookupError as exc:
                last_error = exc
                if exc.code == "RATE_LIMITED":
                    rate_limited_models.append(gemini_model)
                    logger.info("Gemini model {} rate-limited, trying next", gemini_model)
                    continue
                if exc.code == "API_ERROR" and "unsupported" in exc.message.lower():
                    continue
                raise

        if rate_limited_models:
            raise GeminiLookupError(
                "RATE_LIMITED",
                "Gemini web search quota exhausted — specs cannot be fetched reliably without it. "
                "Wait a few minutes and try again, or enter specifications manually.",
            )

        if last_error:
            raise last_error

        raise GeminiLookupError(
            "NOT_FOUND",
            "Could not resolve laptop specifications. Enter details manually.",
        )

    async def lookup_product_image(
        self,
        model_number: str,
        model_name: str | None = None,
        brand_name: str | None = None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        if not self.is_configured:
            return None, None

        model_number = model_number.strip()
        if not model_number:
            return None, None

        brand_line = f"Brand: {brand_name}\n" if brand_name else ""
        name_line = f"Product line: {model_name}\n" if model_name else ""
        prompt = f"""Use Google Search to find a direct HTTPS URL for the official product photo of this exact laptop SKU.

{brand_line}{name_line}Model number / SKU: {model_number}

Rules:
1. Return a DIRECT link to an image file (jpg, jpeg, png, or webp) — not an HTML product page.
2. Prefer official manufacturer CDN URLs (asus.com, dell.com, hp.com, lenovo.com, etc.).
3. The image must match SKU "{model_number}" when possible.
4. Pick the standard front-facing hero product shot.

Respond with ONLY valid JSON: {{"product_image_url": "https://..."}} or {{"product_image_url": null}} if not found."""

        for gemini_model in self._grounded_model_chain():
            try:
                payload = _build_payload(prompt, use_grounding=True)
                body = await self._generate(gemini_model, payload)
                text = _extract_text(body)
                parsed = _parse_json_object(text or "")
                url_str = None
                if parsed and isinstance(parsed, dict):
                    image_url = parsed.get("product_image_url")
                    if image_url is not None:
                        url = str(image_url).strip()
                        if (
                            url.lower() not in {"null", "none", "n/a"}
                            and url.startswith("https://")
                        ):
                            from webstudio_backend.services.product_image_service import (
                                is_suspicious_placeholder_image_url,
                            )

                            if not is_suspicious_placeholder_image_url(url):
                                url_str = url[:512]
                return url_str, body
            except GeminiLookupError as exc:
                if exc.code in {"RATE_LIMITED", "API_ERROR"}:
                    continue
                raise
        return None, None

    async def _finalize_lookup_result(
        self,
        result: dict[str, Any],
        *,
        body: dict[str, Any],
        model_number: str,
        brand_name: str | None,
        model_name: str | None,
    ) -> dict[str, Any]:
        from webstudio_backend.services.product_image_service import resolve_product_image

        image_url = await resolve_product_image(
            model_number=model_number,
            brand_name=brand_name,
            model_name=result.get("model_name") or model_name,
            candidate_url=result.get("product_image_url"),
            grounding_body=body,
        )
        if image_url:
            result["product_image_url"] = image_url
            logger.info("Spec lookup image resolved for {}: {}", model_number, image_url[:120])
        else:
            result["product_image_url"] = None
            logger.warning("Spec lookup found no product image for {}", model_number)
        return result

    async def _generate(self, gemini_model: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.warning("Gemini network error for {}: {}", gemini_model, type(exc).__name__)
            raise GeminiLookupError(
                "API_ERROR",
                "Could not reach Gemini. Check your internet connection and try again.",
            ) from exc

        if response.status_code == 429:
            raise GeminiLookupError("RATE_LIMITED", _parse_rate_limit_message(response))

        if response.status_code in {401, 403}:
            raise GeminiLookupError(
                "API_ERROR",
                "Gemini API key was rejected. Create a new key at https://aistudio.google.com/apikey",
            )

        if response.status_code == 404:
            raise GeminiLookupError(
                "API_ERROR",
                f"Gemini model '{gemini_model}' is not available for this API key.",
            )

        if response.status_code == 400:
            message = _error_message(response)
            raise GeminiLookupError("API_ERROR", message or "Gemini rejected the request.")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Gemini HTTP error for {}: status={}", gemini_model, response.status_code)
            raise GeminiLookupError(
                "API_ERROR",
                "Gemini request failed. Enter specifications manually.",
            ) from exc

        return response.json()


def _build_lookup_prompt(
    model_number: str,
    brand_name: str | None = None,
    model_name: str | None = None,
) -> str:
    brand_line = f"Brand: {brand_name}\n" if brand_name else ""
    name_line = f"Marketing name (if known): {model_name}\n" if model_name else ""
    return f"""You are looking up laptop specifications for inventory entry at a computer retail store.

{brand_line}Model number / SKU: {model_number}
{name_line}
Use Google Search with the exact query: "{model_number} specifications" (include brand if known).

Find the official manufacturer specification page or major retailer listing for this EXACT model number.

Important rules:
1. The SKU "{model_number}" is authoritative — do NOT substitute a different model, product line, or regional variant unless the exact SKU cannot be found anywhere online.
2. Do NOT guess from similar ASUS/Dell/HP model prefixes. If web search does not return this exact SKU, set cpu to null and explain in "notes" — never invent specs.
3. model_name must match the official marketing name from the listing (e.g. "ASUS TUF Gaming A14", not "Vivobook" unless the listing says Vivobook).
4. If only a very close regional variant exists, use its specs but explain in "notes".
3. Extract the full configuration for this SKU: CPU, GPU, RAM, storage, display, colors, OS, battery, weight, ports/wireless.
4. CPU must be the exact chip (e.g. "Intel Core i5-1335U", "AMD Ryzen 5 7530U", "Snapdragon X Elite X1E-78-100") — not a generic family.
5. ram_gb is system RAM as an integer.
6. storage_value is the primary SSD/HDD size (digits only).
7. gpu is the discrete GPU name, integrated graphics name, or null.
8. display must include size, resolution, panel type, and refresh rate when available (e.g. '15.6" FHD (1920×1080) IPS 60Hz' or '14" 2.8K OLED 90Hz').
9. color_options: comma-separated available colors for this SKU, or null.
10. operating_system: pre-installed OS with edition when known (e.g. "Windows 11 Home", "FreeDOS").
11. battery: capacity and/or rated life when published (e.g. "42 Wh, up to 8 hours").
12. weight: machine weight with unit (e.g. "1.45 kg" or "3.2 lbs").
13. connectivity: Wi-Fi/BT generation plus main ports (e.g. "Wi-Fi 6E, Bluetooth 5.3, 2× USB-C, 1× HDMI 2.1").
14. keyboard: backlight, layout, or numpad notes when relevant, or null.
15. memory_type: RAM type when published (e.g. "DDR4", "DDR5", "LPDDR5X"), or null.
16. warranty: standard warranty period for this SKU/region when known (e.g. "1 year onsite"), or null.
17. webcam: camera resolution or features (e.g. "720p HD", "1080p IR with privacy shutter"), or null.
18. audio: speaker/mic details (e.g. "2 speakers, SonicMaster, array mic"), or null.
19. charger: adapter wattage and connector when known (e.g. "65W USB-C"), or null.
20. description: 2–5 sentences for retail staff — product positioning, key selling points, and ideal use case. Plain text only.
21. product_image_url: direct HTTPS URL to a product photo image file (jpg/png/webp) from the official manufacturer or major retailer CDN for this exact SKU — NOT an HTML product page. Use Google Search to find the hero product shot for "{model_number}".

Respond with ONLY valid JSON (no markdown fences) using exactly these keys:
model_name, cpu, gpu, ram_gb, storage_value, storage_unit, storage_type, display, color_options,
operating_system, battery, weight, connectivity, keyboard, memory_type, warranty, webcam, audio, charger,
description, product_image_url, notes

notes: brief source or caveat only (e.g. "Matched official ASUS India listing for X1504VA-D5321WS")."""


def _build_payload(prompt: str, use_grounding: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }
    if use_grounding:
        payload["tools"] = [{"google_search": {}}]
    else:
        payload["generationConfig"]["responseMimeType"] = "application/json"
    return payload


def _parse_lookup_response(
    body: dict[str, Any],
    fallback_name: str,
    *,
    model_number: str,
) -> dict[str, Any] | None:
    text = _extract_text(body)
    if not text:
        return None

    parsed = _parse_json_object(text)
    if not parsed:
        logger.warning("Gemini returned non-JSON text: {}", text[:200])
        return None

    normalized = _normalize_spec(parsed, fallback_name=fallback_name)
    if not normalized.get("cpu"):
        return None
    if normalized.get("ram_gb") is None:
        logger.warning("Gemini spec missing ram_gb for {}", model_number)
        return None
    if not normalized.get("storage_value"):
        logger.warning("Gemini spec missing storage for {}", model_number)
        return None
    if not _response_anchors_model_number(model_number, normalized):
        logger.warning(
            "Gemini spec for {} does not reference the searched SKU in model_name/notes/description",
            model_number,
        )
        return None
    return normalized


def _error_message(response: httpx.Response) -> str:
    try:
        return str(response.json().get("error", {}).get("message", ""))
    except (json.JSONDecodeError, AttributeError):
        return ""


def _parse_rate_limit_message(response: httpx.Response) -> str:
    try:
        message = response.json().get("error", {}).get("message", "")
        if "limit: 0" in message and "gemini-2.0-flash-lite" in message:
            return (
                "gemini-2.0-flash-lite has no free-tier quota on this key. "
                "Set GEMINI_MODEL=gemini-2.5-flash in .env and restart the backend."
            )
        if "Please retry in" in message:
            return f"Gemini rate limit: {message.split('Please retry in')[-1].strip()}"
    except (json.JSONDecodeError, AttributeError):
        pass
    return "Gemini rate limit reached. Wait a minute or set GEMINI_MODEL=gemini-2.5-flash in .env."


def _extract_text(body: dict[str, Any]) -> str | None:
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        return None
    text = parts[0].get("text") if isinstance(parts[0], dict) else None
    return text if isinstance(text, str) else None


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def _normalize_cpu(cpu: str) -> str:
    cleaned = cpu.replace("®", "").replace("™", "").strip()
    match = re.search(
        r"((?:Intel|AMD)\s+(?:Core|Ryzen)\s+[A-Za-z0-9\s\-]+?)(?:\s+Processor|\s+\d+\.?\d*\s*GHz|\s*\(|,|$)",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return cleaned[:128]


def _normalize_gpu(gpu: Any) -> str | None:
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


def _compose_spec_notes(data: dict[str, Any]) -> str | None:
    """Structured extras for stock cards; source citation after ---."""
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


def _normalize_color_options(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a"}:
        return None
    return text[:256]


def _response_anchors_model_number(model_number: str, result: dict[str, Any]) -> bool:
    """Reject guesses that never mention the searched SKU or its family prefix."""
    sku = model_number.strip().upper()
    if not sku:
        return False
    haystack = " ".join(
        str(result.get(key) or "")
        for key in ("model_name", "notes", "description")
    ).upper()
    if sku in haystack:
        return True
    family = sku.split("-", 1)[0]
    if len(family) >= 4 and family in haystack:
        return True
    return sku in str(result.get("model_name") or "").upper()


def _normalize_spec(data: dict[str, Any], fallback_name: str) -> dict[str, Any]:
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
    storage_value = str(storage_raw).strip() if storage_raw is not None and str(storage_raw).strip() else None

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
    notes_str = _compose_spec_notes(data) if any(data.get(key) for key in spec_keys) else (
        str(notes).strip() if notes else None
    )

    description_raw = data.get("description")
    description = str(description_raw).strip() if description_raw else None
    if description and description.lower() in {"null", "none", "n/a"}:
        description = None

    return {
        "model_name": str(data.get("model_name") or fallback_name).strip(),
        "cpu": _normalize_cpu(str(data.get("cpu") or "")),
        "gpu": _normalize_gpu(data.get("gpu")),
        "ram_gb": ram_gb,
        "storage_value": storage_value or "",
        "storage_unit": storage_unit,
        "storage_type": storage_type,
        "display": (str(data.get("display")).strip() or None) if data.get("display") else None,
        "color_options": _normalize_color_options(data.get("color_options")),
        "product_image_url": image_url,
        "description": description,
        "notes": notes_str,
        "source": "gemini",
    }
