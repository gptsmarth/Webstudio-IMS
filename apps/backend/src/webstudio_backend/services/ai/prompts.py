"""Shared AI prompts for product enrichment."""

from __future__ import annotations


def build_spec_lookup_prompt(
    model_number: str,
    *,
    brand_name: str | None = None,
    model_name: str | None = None,
    use_web_search: bool = True,
) -> str:
    brand_line = f"Brand: {brand_name}\n" if brand_name else ""
    name_line = f"Marketing name (if known): {model_name}\n" if model_name else ""
    search_line = (
        f"Use Google Search with these queries in order: "
        f'1) "{model_number}" {brand_name or ""} specifications '
        f'2) site: manufacturer "{model_number}". Prefer the official brand/PSREF/support page.\n\n'
        if use_web_search
        else (
            "Use your knowledge of published manufacturer specifications.\n\n"
            f'CRITICAL: You do NOT have live web search. If you cannot verify the exact SKU "{model_number}", '
            "return cpu as null, confidence_score below 0.5, and explain in notes — never guess from similar models.\n\n"
        )
    )
    return f"""You are looking up laptop specifications for inventory entry at a computer retail store.

{brand_line}Model number / SKU: {model_number}
{name_line}
{search_line}
Find the official manufacturer specification page or major retailer listing for this EXACT model number.

Important rules:
1. The SKU "{model_number}" is authoritative — do NOT substitute a different model, product line, or regional variant unless the exact SKU cannot be found anywhere online.
2. Do NOT guess from similar ASUS/Dell/HP/Lenovo model prefixes. If you cannot find this exact SKU, set cpu to null and explain in "notes" — never invent specs.
3. model_name must match the official marketing name from the listing (e.g. "Lenovo LOQ 15IAX9", not a sibling SKU).
4. If only a very close regional variant exists, use its specs but explain in "notes" and lower confidence_score.
5. Extract the full configuration for this SKU: CPU, GPU, RAM, storage, display, colors, OS, battery, weight, ports/wireless.
6. CPU must be the exact chip (e.g. "Intel Core i5-12450HX", "AMD Ryzen 5 7530U") — not a generic family.
7. ram_gb is system RAM as an integer (e.g. 12, 16, 24).
8. storage_value is the primary SSD/HDD size (digits only).
9. gpu is the discrete GPU name, integrated graphics name, or null.
10. display must include size, resolution, panel type, and refresh rate when available.
11. color_options: SHORT colour names only, comma-separated (e.g. "Luna Grey, Storm Grey"). Max 6 colours. No marketing sentences.
12. operating_system, battery, weight, connectivity, keyboard, memory_type, warranty, webcam, audio, charger — include when published, else null.
13. description: 2–5 sentences for retail staff — product positioning, key selling points, and ideal use case. Plain text only.
14. confidence_score: float 0.0–1.0 for how confident you are the specs match this EXACT SKU (use <0.5 if unsure).
15. Do NOT return product_image_url — images are resolved separately (saves tokens / latency).

Respond with ONLY valid JSON (no markdown fences) using exactly these keys:
model_name, cpu, gpu, ram_gb, storage_value, storage_unit, storage_type, display, color_options,
operating_system, battery, weight, connectivity, keyboard, memory_type, warranty, webcam, audio, charger,
description, notes, confidence_score

notes: brief source or caveat only (e.g. "Matched official Lenovo PSREF for 15IAX9")."""


def build_image_search_query_prompt(
    model_number: str,
    *,
    brand_name: str | None = None,
    model_name: str | None = None,
) -> str:
    brand_line = f"Brand: {brand_name}\n" if brand_name else ""
    name_line = f"Product line: {model_name}\n" if model_name else ""
    return f"""Generate an optimized web image search query to find the official product photo for this laptop SKU.

{brand_line}{name_line}Model number / SKU: {model_number}

Rules:
1. Return a concise search query (5–12 words).
2. Include brand and exact model number.
3. Prefer terms like "official product", "hero image", or "product photo".
4. Do NOT return a URL — only the search query string.

Respond with ONLY valid JSON: {{"image_search_query": "..."}}"""


def default_image_search_query(
    model_number: str,
    *,
    brand_name: str | None = None,
    model_name: str | None = None,
) -> str:
    """Deterministic image query — no AI tokens required."""
    sku = model_number.strip()
    brand = (brand_name or "").strip()
    name = (model_name or "").strip()
    # Prefer brand + exact SKU + official product photo terms for Bing/DDG.
    if brand and name and name.lower() not in sku.lower():
        return f'{brand} {name} "{sku}" official product photo'
    if brand:
        return f'{brand} "{sku}" official product photo laptop'
    return f'"{sku}" official product photo laptop'


def build_accessory_spec_lookup_prompt(
    identifier: str,
    *,
    identifier_type: str = "model_number",
    brand_name: str | None = None,
    model_name: str | None = None,
    use_web_search: bool = True,
) -> str:
    brand = (brand_name or "").strip()
    brand_line = f"Brand: {brand}\n" if brand else ""
    name_line = f"Known name (if any): {model_name}\n" if model_name else ""

    if identifier_type == "part_number":
        id_context = f"""The retailer entered the manufacturer PART NUMBER (product number / SKU / order code) for {brand or "this brand"}.
Part number to look up: {identifier}

Search the web for this exact {brand} part number. Official sources: {brand} support site, {brand} store, authorized retailers (Amazon India, Flipkart, etc.).
The part number and marketing model number are often DIFFERENT — return both when the listing shows both."""
        search_hint = f'"{identifier}" {brand} part number'
    else:
        id_context = f"""The retailer entered the manufacturer MODEL NUMBER / marketing SKU for {brand or "this brand"}.
Model number to look up: {identifier}

Search the web for this exact {brand} accessory model. Official sources: {brand} support site, {brand} store, authorized retailers."""
        search_hint = f'"{identifier}" {brand} accessory model'

    search_line = (
        f"Use Google Search starting with: {search_hint}\n\n"
        if use_web_search
        else (
            "Use your knowledge of published manufacturer specifications.\n\n"
            f'If you cannot verify "{identifier}", set confidence_score below 0.5 and explain in notes.\n\n'
        )
    )
    return f"""You are looking up computer accessory details for inventory entry at a retail store.

{brand_line}{id_context}
{name_line}
{search_line}
Find the official manufacturer or major retailer listing for this EXACT identifier.

Important rules:
1. The entered identifier "{identifier}" is what the user typed — do not substitute a different SKU.
2. model_name must be the official marketing product name (e.g. "ASUS MD100 Silent Wireless Mouse") — NOT the raw part number alone.
3. part_number and model_number are separate fields when the manufacturer publishes both. Do not copy the part number into model_number unless they are genuinely the same on the official listing.
4. accessory_kind must be one of: mouse, keyboard, charger, headset, bag, dock, cable, adapter, storage, other — infer from the product (do not default to "other" if obvious).
5. color_options: SHORT colour/variant names only, comma-separated (e.g. "Black, White"). No long sentences.
6. description: 2–4 sentences for retail staff — key features and compatibility. Plain text only.
7. confidence_score: float 0.0–1.0 for match confidence on this exact identifier.
8. Do NOT return product_image_url — images are resolved separately (saves tokens / latency).

Respond with ONLY valid JSON (no markdown fences) using exactly these keys:
model_name, model_number, part_number, accessory_kind, color_options, description, notes, confidence_score

notes: brief source or caveat only."""
