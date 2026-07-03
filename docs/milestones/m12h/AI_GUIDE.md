---
Title: AI Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# AI Guide

Configure **AI enrichment** for product specs and images (Add Laptop workflow).

---

## 1. Purpose

When staff add inventory, AI can:

- Fetch laptop specifications from the web
- Suggest product image URLs
- Reduce manual data entry

**AI does not** make sales, change inventory status, or access Tally.

---

## 2. Supported providers

| Provider | Setting key | Default model |
|----------|-------------|---------------|
| Google Gemini | `gemini_api_key` | `gemini-2.5-flash` |
| Groq | `groq_api_key` | `llama-3.3-70b-versatile` |
| OpenRouter | `openrouter_api_key` | Configurable |

**Primary provider** and **fallback chain** in Settings → Integrations.

---

## 3. Administrator setup

1. **Settings → Integrations**
2. Enter API key for chosen provider (keys stored encrypted server-side)
3. Set **AI enrichment enabled**
4. **Test AI** — confirm provider responds
5. Save

Free-tier Gemini key: https://aistudio.google.com/apikey

---

## 4. Operator use

1. **Inventory → Add laptop**
2. Enter brand / model search term
3. Tap **Fetch specs** (if button visible)
4. Review suggested specs — edit before save
5. Save item

If AI disabled or offline, enter specs manually.

---

## 5. Privacy and data

| Sent to provider | Not sent |
|------------------|----------|
| Model name search query | Customer PII |
| Public product pages | Serial numbers |
| | Passwords, JWT |

Review provider terms for your region.

---

## 6. Troubleshooting

| Issue | Action |
|-------|--------|
| Fetch failed | Check API key; test in Settings |
| Timeout | Increase `ai_timeout_seconds` |
| Wrong specs | Edit manually; report model name |
| Costs | Use Gemini free tier or disable enrichment |

Office Deployment Wizard validates AI configuration at deploy time.

---

## 7. Disable AI

**Settings → Integrations → AI enrichment enabled → Off**

Add Laptop works fully in manual mode.

---

## 8. Engineering reference

- [MILESTONE_9D AI Report](../../api/MILESTONE_9D_AI_MODERNIZATION_REPORT.md)
- `services/ai/config.py`, `services/ai/health.py`
