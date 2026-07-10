---
Title: Tally Sync Root Cause Analysis
Version: 1.1.0
Status: Resolved — Redesign Implemented
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-10
Related Documents: docs/integrations/tally-erp9/sync-strategy.md, adr/ADR-0011-tally-integration-strategy.md
---

# Tally Sales Synchronization — Root Cause Analysis (P0)

**Audit date:** 2026-07-10  
**Implementation status:** **Fixed** in deterministic redesign (migration `0047_tally_sync_redesign`, serial-only matching).  
**Observed failure:** Invoice `AES/0147/26-27` incorrectly marked laptop `W1N0KD006934044` as sold because a backpack line without a serial entered the model-matching path.

---

## 1. Executive Summary

Wrong inventory deduction occurred when:

1. A Tally line had **no serial**, and  
2. `_match_inventory_by_model()` + `models_equivalent()` (shared token ≥4 chars, e.g. `ASUS`) selected the only available ASUS laptop.

The backpack line amount (~₹1000) was then stored on that wrong sale (with legacy ×1.18 GST helper).

**Remediation (implemented):** Remove all model-based inventory selection. Inventory moves **only** on exact normalized serial match. No-serial / unknown-serial lines become **Additional Products**. Model mismatch after serial match still sells but marks **Completed with Review Required**.

---

## 2. Exact Root Cause (Historical)

### Production evidence — AES/0147/26-27

| Line | Tally product | Serial | Old outcome |
|------|---------------|--------|-------------|
| 0 | ASUS X1407CA-LY1581WS | TBN0CX00904345A | `serial_number_missing` (correct — not in IMS) |
| 1 | CARRY CASE ASUS BACKPACK | *(empty)* | `sale_applied` on wrong laptop via fuzzy model match |

### Unsafe path (removed)

```text
no serial → _match_inventory_by_model(stock_item_name)
         → models_equivalent() token intersection (e.g. "ASUS")
         → exactly one available match → SOLD
```

This path is **permanently deleted**. Regression: `apps/backend/tests/tally/test_tally_aes0147_regression.py`.

---

## 3. Redesign Invariants (Current)

| Rule | Behaviour |
|------|-----------|
| Serial extraction | `BASICUSERDESCRIPTION[0]` → `SERIALNUMBER` → `BATCHALLOCATIONS.SERIALNUMBER` |
| Inventory movement | Exact normalized serial only |
| Case C | No serial / serial not in IMS → Additional Product (no auto Pending Review) |
| Case B | Serial match + model differ → sell + review required |
| Case D/E | Duplicate IMS serial / already sold → review, no sell |
| Amounts | From XML only — no GST estimation |
| Idempotency | Voucher GUID; nested transaction per voucher |
| Audit | Decision log + gzip XML archive |

See `docs/integrations/tally-erp9/sync-strategy.md` v1.3.0 for the frozen matching cases.

---

## 4. Why Incorrect Deduction Must Not Recur

| Risk | Mitigation |
|------|------------|
| No-serial fuzzy sell | Path removed; Additional Product only |
| Brand/token match | Removed |
| Wrong amount | XML line totals; no ×1.18 |
| No audit trail | Decision log + raw XML archive |
| Duplicate import | GUID terminal-status skip |

**Principle:** Correctness over automation. If serial cannot uniquely identify an **available** unit → do not move inventory.

---

## 5. References

| Document | Path |
|----------|------|
| Frozen sync strategy | `docs/integrations/tally-erp9/sync-strategy.md` |
| Migration | `database/migrations/versions/0047_tally_sync_redesign.py` |
| Sync service | `apps/backend/src/webstudio_backend/services/tally_sync_service.py` |
| AES/0147 regression | `apps/backend/tests/tally/test_tally_aes0147_regression.py` |
