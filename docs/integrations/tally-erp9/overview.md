---
Title: Tally ERP 9 Overview
Version: 1.2.0
Status: Frozen
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/integrations/tally-erp9/sync-strategy.md, docs/SYSTEM_ARCHITECTURE.md
---

# Tally ERP 9 Overview

## Purpose

Tally ERP 9 is the **primary source of truth for sales** in WEBSTUDIO IMS. The Tally Integration Service reads invoices from Tally and reflects laptop sales in inventory via the Backend API. IMS **never** writes billing data to Tally.

Manual **Mark as Sold** (Main Admin and Admin only) remains available for exceptional situations when sync is delayed or unavailable.

## Architecture Status

**Fully frozen** — inventory matching strategy finalized in [sync-strategy.md](sync-strategy.md) v1.2.0. No further architectural changes required before Tally Synchronization Engine implementation.

## Reliability Model (Summary)

| Concern | Design |
|---------|--------|
| **Authoritative match** | Serial Number in **`available`** inventory only |
| Model verification | Informational only — runs **after** sale; never blocks sold transition |
| Model normalization | Strip marketing prefixes; compare model numbers; minor differences ignored |
| Model mismatch | Sale still applied; **`product_model_mismatch`** warning notification |
| Invoice state | `tally_processed_invoices` — SUCCESS / PARTIAL_SUCCESS / FAILED |
| Execution history | `tally_sync_logs` — one row per attempt (diagnostics) |
| Partial retry | Failed lines only when PARTIAL_SUCCESS |
| Crash recovery | SUCCESS skip; PARTIAL_SUCCESS resume; FAILED full retry |
| Transactions | Line-level — no invoice-wide rollback |
| Completion | SUCCESS only when all inventory-related lines complete |

## Key Rules (Summary)

| Rule | Behaviour |
|------|-----------|
| Invoice processing | Each line independent; one failure never stops others |
| Matching | Serial Number is **authoritative** — search **`available`** inventory only |
| Product model | Verification **after** sale only; never blocks marking sold |
| Model mismatch | **`product_model_mismatch`** notification — informational; sale already applied |
| Duplicate sale | Serial already **sold** → notification only |
| Audit vs sync log | Business events in Audit Log; statistics in sync log only |

## Related Documents

| Document | Content |
|----------|---------|
| [sync-strategy.md](sync-strategy.md) | **Canonical** — all synchronization rules |
| [data-mapping.md](data-mapping.md) | Tally XML → IMS field mapping |
| [SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md) | §14.3 Tally Integration |
| [DATABASE_DESIGN.md](../../database/DATABASE_DESIGN.md) | §4.10–4.10.2 |
