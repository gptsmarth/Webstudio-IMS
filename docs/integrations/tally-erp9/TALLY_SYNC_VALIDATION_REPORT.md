---
Title: Tally Sync Validation Report
Version: 1.2.0
Status: Lab regression PASSED — Production server certification PENDING
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-10
Related Documents:
  - docs/integrations/tally-erp9/TALLY_SYNC_CONFIGURATION_REPORT.md
  - docs/integrations/tally-erp9/sync-strategy.md
  - docs/integrations/tally-erp9/TALLY_SYNC_ROOT_CAUSE_ANALYSIS.md
---

# Tally Sync Validation Report

## Executive verdict

| Layer | Status | Notes |
|-------|--------|-------|
| **Code redesign + P0 final refinement** | Implemented | Serial-only engine; Case C1/C2; invoice status labels; serial source audit |
| **GUID watermark optimization** | Implemented | Incremental efficiency cursor; GUID remains sole sync identity |
| **Lab / regression suite** | **PASSED** | AES/0147, Cases D/E, crash/idempotency, mixed invoice, watermark scenarios 1–4 |
| **Live production (WEBSTUDIO-SERVER + Tally)** | **NOT CERTIFIED HERE** | Must be signed off on the office server after deploy |

---

## 1. Summary of P0 final refinements

| Refinement | Change |
|------------|--------|
| Case C split | **C1** no serial → Additional Product; **C2** serial not in IMS → Unmatched Serialized Item |
| Invoice status | Operator labels: `processed`, `processed_with_warnings`, `skipped`, `failed` (mapped from `processing_status`) |
| Restart | Documented + tested: `last_imported_voucher_date` → today + GUID filter |
| Sale Details API | Tracked products, additional products, unmatched serialized items, invoice totals, invoice status |
| Serial source | Stored on sale; exposed to **Main Admin** as `BASICUSERDESCRIPTION[0]` / `SERIALNUMBER` / `BATCHALLOCATIONS.SERIALNUMBER` |
| Parser safety | Empty `BASICUSERDESCRIPTION.LIST` never throws; falls back to SERIALNUMBER / BATCH |
| GUID watermark | Persist checkpoint; fast-skip historical vouchers after `last_processed_guid`; Main Admin `sync_checkpoint` diagnostics |
| Migration | `0048_tally_sync_refinement`, `0049_tally_guid_watermark` |

---

## 2. Updated Case C behaviour

| Case | Condition | Storage | Inventory |
|------|-----------|---------|-----------|
| **C1** | No serial extracted | Additional Product | No change |
| **C2** | Serial extracted, not in IMS | Unmatched Serialized Item (product, serial, amount, reason “Serial not managed in IMS”) | No change; no auto review queue |

AES/0147 lab: X1407 serial → **C2**; backpack → **C1**; victim laptop stays AVAILABLE.

---

## 3. Invoice-level status

| Operator label | Persisted `processing_status` | Example |
|----------------|-------------------------------|---------|
| Processed | `success` | Laptop + mouse sold, bag attached |
| Processed With Warnings | `completed_with_review_required` / `partial_success` | Model mismatch review |
| Skipped | `skipped` | Duplicate GUID |
| Failed | `failed` | Transaction rollback |

Exposed on Sale Details as `invoice_status`.

---

## 4. Restart validation

| Check | Result |
|-------|--------|
| From = `last_imported_voucher_date`, To = current date | Code + unit test |
| GUID filter prevents duplicate sale/deduction | Lab idempotency tests PASS |
| Overnight invoices not skipped | Window includes last imported date |
| GUID watermark fast-skip after restart | Lab scenarios 1 & 4 PASS |
| Power / Windows / scheduler restart | Checkpoint fields + watermark resume; live confirm on server |

---

## 4b. GUID watermark optimization validation

| Scenario | Expected | Lab |
|----------|----------|-----|
| **1** Server OFF overnight; Sales + NEW SALE created; restart | Only new GUIDs imported; watermark skips prior | PASS (`test_scenario1_overnight_restart_imports_only_new_guids`) |
| **2** Day Book with 300 historical + new | Watermark skips 300; only new fully processed | PASS (`test_scenario2_daybook_watermark_skips_full_processing`) |
| **3** Duplicate scheduler execution | No duplicate inventory / sales | PASS (`test_scenario3_duplicate_scheduler_no_double_inventory`) |
| **4** Power failure mid-day; resume | Watermark resumes; no skip / no duplicate | PASS (`test_scenario4_power_failure_watermark_resumes_without_skip`) |

Invariant checks (all PASS in lab):

- GUID remains sole synchronization identity  
- Invoice numbers / MasterID never used for identity  
- Matching / serial extraction / inventory movement unchanged  

---

## 5. Parser fallback validation

| Check | Result |
|-------|--------|
| First non-empty BASICUSERDESCRIPTION[0] | PASS |
| Empty BASICUSERDESCRIPTION.LIST → SERIALNUMBER | PASS (`test_empty_basicuserdescription_list_falls_back_to_serialnumber`) |
| No parser exception on empty list | PASS |

---

## 6. Regression test results (lab)

```text
pytest tests/tally/test_tally_aes0147_regression.py \
       tests/tally/test_tally_case_de_review.py \
       tests/tally/test_tally_certification.py \
       tests/tally/test_tally_mixed_invoice_regression.py \
       tests/tally/test_tally_accessory_sales.py \
       tests/tally/test_tally_api.py \
       tests/tally/test_tally_incremental_sync.py \
       tests/tally/test_tally_guid_watermark.py \
       tests/tally/test_tally_enterprise_metadata.py -q
```

**Result (2026-07-10):** all selected tests **PASSED** (including GUID watermark scenarios 1–4).

### Mixed production-shaped invoice

| Line | Expected | Lab |
|------|----------|-----|
| Laptop serial ABC123… | Sale + deduct | PASS |
| Backpack (no serial) | Additional Product | PASS |
| Mouse serial XYZ999… | Sale + deduct | PASS |
| One GUID / XML archive / totals | Present | PASS |
| No review required | PASS | PASS |

---

## 7. Safety questions

| Question | Answer |
|----------|--------|
| Can wrong inventory still be deducted? | **No** |
| Can invoices be skipped incorrectly? | **No** (GUID + date window + watermark only after prior success) |
| Can invoices be imported twice? | **No** |
| Can restart corrupt sync? | **No** (nested txn + GUID + watermark resume) |
| Can accessories deduct laptops? | **No** |
| Can model names influence inventory? | **No** |
| Does watermark replace GUID idempotency? | **No** — efficiency only |
| Does AES/0147 behave correctly? | **Yes (lab)** — C2 + C1, no wrong sale |
| Are unmatched serials visible? | **Yes** — Unmatched Serialized Item on Sale Details |

---

## 8. Files modified (watermark optimization)

- `integrations/tally/incremental_sync.py` — `partition_by_guid_watermark`
- `services/tally_sync_service.py` — watermark fast-path + checkpoint persistence
- `services/tally_dashboard_service.py` — `operational.sync_checkpoint`
- `infrastructure/database/models/tally_company_sync.py` + repository
- `database/migrations/versions/0049_tally_guid_watermark.py`
- Tests: `test_tally_guid_watermark.py`; enterprise metadata checkpoint allowlist
- Docs: this report; `TALLY_SYNC_CONFIGURATION_REPORT.md` §6

---

## 9. Database changes

### `0048_tally_sync_refinement`

| Change | Detail |
|--------|--------|
| Enum | `tally_line_outcome.unmatched_serialized_item` |
| Column | `tally_processed_invoice_line.is_unmatched_serialized` |
| Column | `sales.serial_source` |
| Index | `ix_tally_processed_invoice_line_unmatched` |

### `0049_tally_guid_watermark`

| Change | Detail |
|--------|--------|
| Column | `tally_company_sync.last_processed_invoice_number` |
| Column | `tally_company_sync.last_processed_voucher_type` |

---

## 10. New / updated tests

| Test | Coverage |
|------|----------|
| `test_mixed_laptop_backpack_mouse_invoice` | Real mixed invoice |
| `test_empty_basicuserdescription_list_falls_back_to_serialnumber` | Parser safety |
| AES/0147 assertions | C2 for unknown serial; C1 for backpack |
| `test_tally_guid_watermark.py` | Watermark scenarios 1–4 + partition unit tests |

---

## 11. CI quality (pre-push)

| Check | Status |
|-------|--------|
| `ruff check` (backend src + tally tests + migrations 0047–0049) | PASS |
| `black --check` (same) | PASS |
| `pnpm typecheck` | PASS |
| Selected tally pytest (incl. watermark) | PASS |

---

## 12. Production server certification (REQUIRED)

Deploy migrations **0047** + **0048** + **0049**, restart backend, then complete live checklist on WEBSTUDIO-SERVER (connectivity, overnight resume, watermark diagnostics, AES behaviour).  

**Production certification status:** ☐ PENDING ☐ PASSED ☐ FAILED
