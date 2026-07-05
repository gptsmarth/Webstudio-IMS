"""Track which Gemini model succeeds most often for faster spec lookups."""

from __future__ import annotations

from threading import Lock

_lock = Lock()
_last_successful_model: str | None = None
_success_counts: dict[str, int] = {}


def record_gemini_model_success(model: str) -> None:
    name = model.strip()
    if not name:
        return
    global _last_successful_model
    with _lock:
        _last_successful_model = name
        _success_counts[name] = _success_counts.get(name, 0) + 1


def most_successful_gemini_model() -> str | None:
    with _lock:
        if _success_counts:
            return max(_success_counts.items(), key=lambda item: item[1])[0]
        return _last_successful_model


def reset_gemini_model_stats() -> None:
    global _last_successful_model
    with _lock:
        _last_successful_model = None
        _success_counts.clear()
