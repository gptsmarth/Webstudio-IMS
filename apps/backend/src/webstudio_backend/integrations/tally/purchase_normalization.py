"""Deterministic model-number normalization for Purchase Import model lookup.

This module is used ONLY by the Purchase Import model lookup. It MUST NOT be
used anywhere in the Sales sync path (serial-only matching is unchanged).

Rules (deterministic, no fuzzy matching, no AI, no token similarity):
  1. Uppercase.
  2. Trim.
  3. Collapse multiple internal spaces to a single space.
  4. Remove ONLY a leading brand prefix (brand name or brand short name).

Examples:
  ("ASUS F1504FA-BQ2113WS", "ASUS")     -> "F1504FA-BQ2113WS"
  ("HP 15-FD0456TU", "HP")              -> "15-FD0456TU"
  ("LENOVO 82XQ00W4IN", "Lenovo")       -> "82XQ00W4IN"
  ("Carry Case", "ASUS")                -> "CARRY CASE"   (no brand prefix present)
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

_WHITESPACE_RE = re.compile(r"\s+")
# Punctuation that should not block a token match (e.g. "MD-102" vs "MD102").
_NOISE_RE = re.compile(r"[^A-Z0-9 ]+")


def _collapse(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip().upper())


def _strip_leading_prefix(value: str, prefix: str | None) -> str:
    """Remove a single leading ``prefix`` token boundary from ``value``.

    Both inputs must already be collapsed/uppercased. The prefix is removed only
    when it appears at the start followed by a space or hyphen (a real word
    boundary), so e.g. brand "HP" never strips the "HP" inside "HPX123".
    """
    if not prefix:
        return value
    normalized_prefix = _collapse(prefix)
    if not normalized_prefix:
        return value
    if value == normalized_prefix:
        return value
    for separator in (" ", "-"):
        candidate = f"{normalized_prefix}{separator}"
        if value.startswith(candidate):
            return value[len(normalized_prefix) :].lstrip(" -").strip()
    return value


def normalize_model_number(
    raw_model: str,
    *,
    brand_name: str | None = None,
    brand_short_name: str | None = None,
) -> str:
    """Return the deterministically normalized model number for lookup."""
    collapsed = _collapse(raw_model or "")
    if not collapsed:
        return ""
    # Try the longer prefix first so "ASUS" beats a short-name of "AS".
    prefixes = sorted(
        {p for p in (brand_name, brand_short_name) if p},
        key=lambda value: len(value),
        reverse=True,
    )
    for prefix in prefixes:
        stripped = _strip_leading_prefix(collapsed, prefix)
        if stripped != collapsed:
            return stripped
    return collapsed


def models_match(
    raw_model: str,
    ims_model_number: str,
    *,
    brand_name: str | None = None,
    brand_short_name: str | None = None,
) -> bool:
    """Exact comparison after deterministic normalization of both sides."""
    left = normalize_model_number(
        raw_model, brand_name=brand_name, brand_short_name=brand_short_name
    )
    right = normalize_model_number(
        ims_model_number, brand_name=brand_name, brand_short_name=brand_short_name
    )
    return bool(left) and left == right


# Minimum compacted length for one model number to be considered a partial
# ("somewhere in between") match of another. Guards against short fragments
# (e.g. "15", "PRO") matching broadly. Real model numbers comfortably exceed it.
PARTIAL_MODEL_MIN_COMPACT_LEN = 5


def models_partial_match(
    raw_model: str,
    ims_model_number: str,
    *,
    brand_name: str | None = None,
    brand_short_name: str | None = None,
) -> bool:
    """True when one normalized model number contains the other (compact form).

    This is a *suggestion-only* signal for the laptop model lookup — it is never
    used to auto-select and never touches the Sales sync path. It exists so a
    catalogue entry that carries an extra base-model suffix still surfaces, e.g.
    IMS ``"S3407QA-KP027WS(S3407QA)"`` vs the Tally bill ``"S3407QA-KP027WS"``.

    Both sides are compacted (spaces/punctuation removed) so ``(S3407QA)`` and
    ``-`` never block the containment test. Exact matches return ``False`` here
    (the caller reports those separately) and a minimum length guard prevents
    tiny fragments from matching everything.
    """
    left = _compact(
        normalize_model_number(raw_model, brand_name=brand_name, brand_short_name=brand_short_name)
    )
    right = _compact(
        normalize_model_number(
            ims_model_number, brand_name=brand_name, brand_short_name=brand_short_name
        )
    )
    if not left or not right or left == right:
        return False
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if len(shorter) < PARTIAL_MODEL_MIN_COMPACT_LEN:
        return False
    return shorter in longer


# ---------------------------------------------------------------------------
# Accessory fuzzy matching (Purchase Import ACCESSORY lookup ONLY).
#
# Accessories arrive from Tally as free-text stock item names (e.g.
# "ASUS MD102 SILENT") while the IMS catalogue may store them under a terse
# part number / model number (e.g. "MD102"). Exact normalization is too strict
# here, so accessory lookup uses a bounded fuzzy score. This is deliberately
# kept OUT of the laptop path and the Sales sync path — laptops still use the
# deterministic exact ``normalize_model_number`` match above.
# ---------------------------------------------------------------------------

# Score at or above which a single candidate can be auto-selected in the UI.
ACCESSORY_AUTO_SELECT_SCORE = 0.9
# Minimum score for a candidate to be surfaced as a suggestion at all.
ACCESSORY_SUGGEST_SCORE = 0.5


def _alnum(value: str) -> str:
    """Collapsed + brand-agnostic form with punctuation removed (kept spaced)."""
    return _WHITESPACE_RE.sub(" ", _NOISE_RE.sub(" ", _collapse(value))).strip()


def _compact(value: str) -> str:
    """Fully compacted form — all spaces and punctuation removed (MD-102 -> MD102)."""
    return _NOISE_RE.sub("", _collapse(value).replace(" ", ""))


def _tokens(value: str) -> set[str]:
    return {token for token in _alnum(value).split(" ") if token}


def _fuzzy_ratio(left: str, right: str) -> float:
    left_clean = _alnum(left)
    right_clean = _alnum(right)
    if not left_clean or not right_clean:
        return 0.0
    return SequenceMatcher(None, left_clean, right_clean).ratio()


def accessory_match_score(
    query: str,
    *,
    candidate_model_number: str | None,
    candidate_part_number: str | None = None,
    candidate_model_name: str | None = None,
    brand_name: str | None = None,
    brand_short_name: str | None = None,
) -> float:
    """Return a 0..1 confidence that an IMS accessory matches a Tally query.

    ``query`` is the Tally stock item name (or operator-typed identifier). It is
    compared against the catalogue accessory's part number, model number, and
    model name. Brand prefixes are stripped from both sides first so
    "ASUS MD102 SILENT" and "MD102" line up.

    Signals (highest wins):
      * exact normalized identifier match                        -> 1.0
      * identifier is a whole token inside the query             -> 0.95
      * every identifier token present in the query              -> 0.9
      * identifier is a substring of the query (or vice versa)   -> 0.85
      * character-level fuzzy ratio on identifiers               -> up to 0.8
      * model-name token overlap / fuzzy ratio (weaker signal)   -> up to 0.75
    """
    normalized_query = normalize_model_number(
        query, brand_name=brand_name, brand_short_name=brand_short_name
    )
    if not normalized_query:
        return 0.0
    query_tokens = _tokens(normalized_query)
    query_alnum = _alnum(normalized_query)
    query_compact = _compact(normalized_query)
    query_token_compacts = {_compact(token) for token in query_tokens if _compact(token)}

    best = 0.0
    for identifier in (candidate_part_number, candidate_model_number):
        if not identifier:
            continue
        candidate = normalize_model_number(
            identifier, brand_name=brand_name, brand_short_name=brand_short_name
        )
        candidate_alnum = _alnum(candidate)
        candidate_compact = _compact(candidate)
        if not candidate_compact:
            continue
        if candidate_compact == query_compact:
            return 1.0
        candidate_tokens = _tokens(candidate)
        # Whole-token match ignoring punctuation/spaces (MD-102 == "MD102" token).
        if candidate_compact in query_token_compacts:
            best = max(best, 0.95)
        if candidate_tokens and candidate_tokens <= query_tokens:
            best = max(best, 0.9)
        # Compact substring either direction ("MD102" inside "MD102SILENT").
        # Guarded to >=3 chars so a stray "X"/"AC" never matches everything.
        if len(candidate_compact) >= 3 and (
            candidate_compact in query_compact or query_compact in candidate_compact
        ):
            best = max(best, 0.9)
        if candidate_alnum and (candidate_alnum in query_alnum or query_alnum in candidate_alnum):
            best = max(best, 0.85)
        best = max(best, _fuzzy_ratio(normalized_query, candidate) * 0.8)

    if candidate_model_name:
        name = normalize_model_number(
            candidate_model_name, brand_name=brand_name, brand_short_name=brand_short_name
        )
        name_tokens = _tokens(name)
        if name_tokens and query_tokens:
            overlap = len(name_tokens & query_tokens) / len(name_tokens | query_tokens)
            best = max(best, overlap * 0.75)
        best = max(best, _fuzzy_ratio(normalized_query, name) * 0.7)

    return round(min(best, 1.0), 4)
