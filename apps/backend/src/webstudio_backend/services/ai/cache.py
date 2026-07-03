"""Product enrichment cache backed by system_settings JSON."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from webstudio_backend.infrastructure.database.enums import SettingValueType
from webstudio_backend.infrastructure.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from webstudio_backend.services.ai.spec_normalization import (
    normalize_brand_name,
    normalize_model_number,
)

_CACHE_KEY = "ai_enrichment_cache"
_MAX_ENTRIES = 500


def _cache_lookup_key(model_number: str, brand_name: str | None) -> str:
    brand = (normalize_brand_name(brand_name) or "").upper()
    sku = normalize_model_number(model_number)
    return f"{brand}|{sku}"


class EnrichmentCacheService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SystemSettingRepository(session)

    async def _load_cache(self) -> dict[str, Any]:
        raw = await self._repo.get_string(_CACHE_KEY)
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _save_cache(self, cache: dict[str, Any]) -> None:
        if len(cache) > _MAX_ENTRIES:
            # Drop oldest entries by insertion order.
            overflow = len(cache) - _MAX_ENTRIES
            for key in list(cache.keys())[:overflow]:
                cache.pop(key, None)
        await self._repo.set_value(
            _CACHE_KEY,
            json.dumps(cache),
            value_type=SettingValueType.JSON,
        )

    async def get(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
    ) -> dict[str, Any] | None:
        cache = await self._load_cache()
        entry = cache.get(_cache_lookup_key(model_number, brand_name))
        if not isinstance(entry, dict):
            return None
        payload = entry.get("payload")
        return payload if isinstance(payload, dict) else None

    async def set(
        self,
        model_number: str,
        *,
        brand_name: str | None,
        payload: dict[str, Any],
        provider: str,
    ) -> None:
        cache = await self._load_cache()
        cache[_cache_lookup_key(model_number, brand_name)] = {
            "provider": provider,
            "payload": payload,
        }
        await self._save_cache(cache)

    async def delete(
        self,
        model_number: str,
        *,
        brand_name: str | None = None,
    ) -> None:
        cache = await self._load_cache()
        cache.pop(_cache_lookup_key(model_number, brand_name), None)
        await self._save_cache(cache)
