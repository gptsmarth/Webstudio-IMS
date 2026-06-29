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
        f'Use Google Search with the exact query: "{model_number} specifications" (include brand if known).\n\n'
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
2. Do NOT guess from similar ASUS/Dell/HP model prefixes. If you cannot find this exact SKU, set cpu to null and explain in "notes" — never invent specs.
3. model_name must match the official marketing name from the listing (e.g. "ASUS TUF Gaming A14", not "Vivobook" unless the listing says Vivobook).
4. If only a very close regional variant exists, use its specs but explain in "notes".
5. Extract the full configuration for this SKU: CPU, GPU, RAM, storage, display, colors, OS, battery, weight, ports/wireless.
6. CPU must be the exact chip (e.g. "Intel Core i5-1335U", "AMD Ryzen 5 7530U") — not a generic family.
7. ram_gb is system RAM as an integer.
8. storage_value is the primary SSD/HDD size (digits only).
9. gpu is the discrete GPU name, integrated graphics name, or null.
10. display must include size, resolution, panel type, and refresh rate when available.
11. color_options: comma-separated available colors for this SKU, or null.
12. operating_system, battery, weight, connectivity, keyboard, memory_type, warranty, webcam, audio, charger — include when published, else null.
13. description: 2–5 sentences for retail staff — product positioning, key selling points, and ideal use case. Plain text only.
14. confidence_score: float 0.0–1.0 indicating how confident you are the specs match this exact SKU.
15. Do NOT return product_image_url — images are resolved separately.

Respond with ONLY valid JSON (no markdown fences) using exactly these keys:
model_name, cpu, gpu, ram_gb, storage_value, storage_unit, storage_type, display, color_options,
operating_system, battery, weight, connectivity, keyboard, memory_type, warranty, webcam, audio, charger,
description, notes, confidence_score

notes: brief source or caveat only (e.g. "Matched official ASUS India listing for X1504VA-D5321WS")."""


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
    parts = [brand_name, model_name, model_number, "official product"]
    return " ".join(part.strip() for part in parts if part and part.strip())
