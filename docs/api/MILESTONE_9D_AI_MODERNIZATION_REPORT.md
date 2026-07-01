# Milestone 9D — AI & Integration Layer Modernization Report

**Date:** 2026-06-27  
**Scope:** `apps/backend/src/webstudio_backend/services/ai/` and integration settings  
**Status:** Complete — **stop for review**

---

## Executive Summary

The AI integration was already structured as a provider framework from prior work. Milestone 9D **formalized and completed** the modernization:

- **Groq is now the default primary provider** with **Gemini as automatic fallback**
- **Mock provider** remains available for tests and offline UAT
- Application code routes through **`ProductEnrichmentService`** and the **`AIProvider` interface** — no direct provider SDK calls outside `services/ai/providers/`
- **Structured logging** added for enrichment orchestration
- Existing enrichment behaviour preserved: caching, DB reuse, validation, image resolution, health tracking, connection tests

---

## 1. Provider Architecture

### Common Interface (`AIProvider` ABC)

```python
class AIProvider(ABC):
    provider_id: ProviderId

    def is_configured(self) -> bool: ...
    async def enrich_product_spec(model_number, *, brand_name, model_name) -> EnrichmentResult: ...
    async def generate_image_search_query(...) -> str: ...
    async def test_connection(self) -> ProviderTestResult: ...
```

### Implemented Providers

| Provider | Role | Web Search | Validation |
|----------|------|------------|------------|
| **Groq** | **Default primary** | No (knowledge-only) | Strict (confidence ≥ 0.95, SKU anchoring) |
| **Gemini** | **Automatic fallback** | Yes (Google Search grounding) | Relaxed for grounded responses |
| **OpenRouter** | Optional tertiary | No | Strict (same as Groq) |
| **Mock** | Tests / UAT | N/A | Deterministic hash-based specs |

### Factory (`providers/factory.py`)

- `create_provider(provider_id, config) -> AIProvider`
- `build_provider_chain(config) -> list[AIProvider]` — deduplicated, ordered by `ai_fallback_chain`

---

## 2. Provider Selection & Defaults (Changed in 9D)

| Setting | Previous Default | New Default |
|---------|------------------|-------------|
| `ai_primary_provider` | `gemini` | **`groq`** |
| `ai_fallback_chain` | `["gemini"]` | **`["groq", "gemini"]`** |

Constants: `DEFAULT_PRIMARY_PROVIDER`, `DEFAULT_FALLBACK_CHAIN` in `services/ai/config.py`.

Resolution order: DB `system_settings` → environment variables → code defaults.

---

## 3. API Key Management

| Key | Provider | Masked in API |
|-----|----------|---------------|
| `groq_api_key` | Groq | Yes (`••••••••1234`) |
| `gemini_api_key` | Gemini | Yes |
| `openrouter_api_key` | OpenRouter | Yes |

- **Read:** `GET /api/v1/settings` → `integrations` group
- **Write:** `PATCH /api/v1/settings/integrations` with `clear_*_api_key` flags
- **Env fallbacks:** `GROQ_API_KEY`, `GEMINI_API_KEY` in `core/config.py`
- **Backup:** AI keys excluded/redacted in backup manifests

---

## 4. Provider Health

`AIProviderHealthTracker` (in-memory, per-process):

| Metric | Description |
|--------|-------------|
| `requests` | Total enrichment attempts |
| `failures` | Failed attempts |
| `rate_limits` | 429 responses |
| `quota_exceeded` | Quota/billing exhaustion |
| `last_error` | Most recent error message |
| `last_success_at` | ISO timestamp of last success |
| `status` | `healthy` / `degraded` / `unavailable` / `not_configured` |

Exposed via `integrations.ai_provider_health` in settings API.

---

## 5. Connection Test

`POST /api/v1/settings/integrations/ai/test`

```json
{ "provider": "groq" }
```

Returns: `{ provider, success, message, latency_ms }`

Orchestrated by `ProductEnrichmentService.test_provider()` with structured `provider_test` logging.

---

## 6. Automatic Fallback

`ProductEnrichmentService.lookup_laptop_spec()` pipeline:

```
1. Config load (resolve_ai_config)
2. Cache check (ai_enrichment_cache)
3. DB reuse (existing ProductModel with CPU)
4. Provider chain walk (groq → gemini → …)
5. Retry loop (ai_retry_count total attempts, backoff 3s × attempt)
6. Image finalization (web scraper, not LLM)
7. Cache write
```

Fallback triggers on: `NOT_FOUND`, `RATE_LIMITED`, `TIMEOUT`, `QUOTA_EXCEEDED`, `API_ERROR`.

Unconfigured providers are skipped (mock always allowed for tests).

---

## 7. Caching

`EnrichmentCacheService` — JSON store in `system_settings.ai_enrichment_cache`:

- Key: `{brand}:{sku}` (normalized)
- Max 500 entries (LRU eviction)
- Stale entries rejected via `validate_enrichment_payload()` and refreshed

---

## 8. Retry Logic

| Setting | Meaning |
|---------|---------|
| `ai_retry_count` | **Total** lookup attempts (not "extra" retries) |
| Default | `2` (1 initial + 1 follow-up) |
| Backoff | `3s × attempt_number` between full chain retries |
| Rate-limit aware | Retries when any provider returned rate-limit/quota/timeout |

---

## 9. Structured Logging (New in 9D)

`services/ai/logging.py` — loguru `bind()` with `layer=ai`:

| Event | When |
|-------|------|
| `enrichment_start` | Chain begins |
| `enrichment_retry` | Backoff retry scheduled |
| `provider_attempt` | Provider invoked |
| `provider_success` | Enrichment succeeded |
| `provider_failure` | Provider returned error |
| `cache_hit` / `cache_stale` | Cache behaviour |
| `database_reuse` | Existing model reused |
| `provider_test` | Connection test result |

All events include structured fields (`sku`, `provider`, `duration_ms`, `error_code`, etc.) for log aggregation.

---

## 10. Decoupling from Specific Providers

### Application Entry Points (provider-agnostic)

| Caller | Uses |
|--------|------|
| `POST /product-models/spec-lookup` | `ProductEnrichmentService` |
| `POST /settings/integrations/ai/test` | `ProductEnrichmentService.test_provider()` |
| Settings read/write | `resolve_ai_config()` |

### Legacy Shim (backward compat only)

`GeminiSpecService` — delegates to `ProductEnrichmentService` when DB session present; session-less mode uses `create_provider()` factory (no direct `GeminiProvider` import).

### Removed Direct Dependencies (9D)

- `product_models.py` — removed unused `GeminiLookupError` import
- `product_image_service.py` — removed `GeminiSpecService` parameter

Provider implementations remain isolated in `services/ai/providers/`.

---

## 11. Enrichment Functionality Preserved

| Feature | Status |
|---------|--------|
| Laptop spec auto-fetch by SKU | ✅ |
| Brand/model name hints | ✅ |
| Multi-field response (CPU, GPU, RAM, storage, display, colors, notes) | ✅ |
| Anti-hallucination validation (SKU anchoring, ASUS line matching) | ✅ |
| Confidence scoring | ✅ |
| Product image resolution (scraper + grounding URLs) | ✅ |
| Error codes for desktop retry logic | ✅ |
| Desktop integrations UI (keys, chain, test buttons) | ✅ |
| Mock provider for automated tests | ✅ |

---

## 12. Files Changed in 9D

| File | Change |
|------|--------|
| `services/ai/logging.py` | **New** — structured logging helpers |
| `services/ai/config.py` | Groq default primary + fallback chain constants |
| `services/ai/types.py` | Default `AIProviderConfig` → groq/gemini |
| `services/ai/enrichment_service.py` | Structured logging integration |
| `services/ai/__init__.py` | Expanded public exports |
| `services/settings_registry.py` | Default settings → groq/gemini |
| `services/gemini_spec_service.py` | Factory-based provider creation |
| `services/product_image_service.py` | Removed Gemini coupling |
| `api/routers/product_models.py` | Clean imports |
| `tests/product_model/test_ai_providers.py` | Default + groq-fallback tests |
| `apps/desktop/.../SettingsPanels.tsx` | Fallback default → groq, gemini |

---

## 13. Test Results

Run with PostgreSQL available:

```bash
cd apps/backend
../../.venv/bin/python -m pytest tests/product_model/test_ai_providers.py tests/product_model/test_ai_validation.py tests/product_model/test_gemini_spec_service.py -v
```

### New / Updated Tests

| Test | Validates |
|------|-----------|
| `test_default_ai_config_uses_groq_primary` | Groq default in config |
| `test_parse_fallback_chain_defaults_to_groq_gemini` | Fallback chain defaults |
| `test_enrichment_service_fallback_to_mock_when_groq_not_configured` | Groq skipped → mock |
| `test_enrichment_service_fallback_to_mock_when_gemini_not_configured` | Gemini skipped → mock (existing) |
| `test_enrichment_service_uses_mock_provider` | End-to-end mock enrichment |
| `test_mock_provider_*` | Mock provider contract |
| `test_ai_validation` | Strict/relaxed validation rules |

---

## 14. Recommended Follow-Ups (Post-Review)

- Desktop: update log messages that still say "via Gemini" to use dynamic `provider` from API response
- Consider persisting `AIProviderHealthTracker` stats to DB for multi-worker deployments
- Add OpenRouter to desktop provider dropdown labels if not already visible
- Optional: migrate `GeminiSpecService` callers fully to `ProductEnrichmentService` and deprecate shim

---

**Next step:** Review this report. No Flutter or new provider implementations until approved.
