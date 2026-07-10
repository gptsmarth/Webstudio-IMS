---
Title: Tally Sync Strategy
Version: 1.3.0
Status: Frozen
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-10
Related Documents: docs/SYSTEM_ARCHITECTURE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/database/DATABASE_DESIGN.md, docs/api/API_SPECIFICATION.md, docs/integrations/tally-erp9/TALLY_SYNC_ROOT_CAUSE_ANALYSIS.md
---

# Tally Sync Strategy

> **Architecture status:** **Frozen (v1.3.0)** — deterministic serial-only matching. Inventory movement **must never** depend on model names, brand tokens, fuzzy matching, or “first available” selection. Implementation must follow this document exactly.

## 1. Source of Truth

| System | Role |
|--------|------|
| **Tally ERP 9** | Primary source of truth for **sales** — invoices are read from Tally |
| **WEBSTUDIO IMS (PostgreSQL)** | Authoritative source of truth for **inventory state** |

Sales are normally synchronized from Tally. The IMS **must** continue supporting manual **Mark as Sold** for **Main Admin** and **Admin** only — for exceptional situations when Tally sync is delayed or unavailable. Manual sales generate normal audit entries (`sale.reflect`, `inventory.transition`) with `sale_source = manual`.

**Billing boundary:** IMS **never** creates invoices, credit notes, or billing entries in Tally.

---

## 2. Invoice Processing Model

A Tally invoice is **never** treated as a single inventory record.

Every inventory-related line item is processed **independently** inside **one database transaction per voucher**. If anything fails, the entire voucher rolls back — never partially import a voucher.

**GUID is authoritative identity.** Processed voucher GUIDs are never reprocessed. Invoice numbering is not used for idempotency.

---

## 3. Serial Extraction (Production)

Production XML stores serials in `BASICUSERDESCRIPTION.LIST`. The **first** `BASICUSERDESCRIPTION` is always the product serial; later entries are remarks only.

| Priority | Source |
|----------|--------|
| 1 | `BASICUSERDESCRIPTION.LIST` → **first** `BASICUSERDESCRIPTION` only |
| 2 | Direct `SERIALNUMBER` |
| 3 | `BATCHALLOCATIONS.LIST` / `SERIALNUMBER` |

**Do not** regex-scan all descriptions. **Do not** use heuristic serial detection.

Normalize for comparison only: trim + uppercase. Keep the original value unchanged.

---

## 4. Inventory Matching (Cases A–E)

**Removed permanently:** `_match_inventory_by_model()`, `models_equivalent()`, shared-token / brand / fuzzy / AI matching, and any automatic inventory deduction using model names.

For every inventory line:

1. Extract serial
2. Search IMS by **exact normalized serial**

| Case | Condition | Inventory | Sale | Status |
|------|-----------|-----------|------|--------|
| **A** | Serial found, model matches | Deduct | Create | Completed |
| **B** | Serial found, model differs | Deduct (serial authoritative) | Create | **Completed with Review Required** — store invoice model, IMS model, serial, reason |
| **C1** | No serial extracted | **No change** | Store as **Additional Product** |
| **C2** | Serial extracted, not in IMS | **No change** | Store as **Unmatched Serialized Item** (visible; reason: Serial not managed in IMS; no auto review) |
| **D** | Duplicate serial rows in IMS | **No change** | None | **Review Required** |
| **E** | Serial already sold | **No change** | No duplicate | **Review Required** |

Non-`available` / non-`sold` statuses (e.g. reserved) → **Review Required**, no sell.

### 4.1 Accessories and multi-serial invoices

- Accessory **with** matching IMS serial → sell and deduct.
- Accessory **without** serial → Additional Product (no deduction).
- Multiple serialized products on one voucher each deduct independently; all remain linked to the same voucher GUID.

### 4.2 Amounts

Read line amounts and tax fields from XML. **Do not estimate GST** (no ×1.18). Store invoice totals from XML: subtotal, discount, round off, CGST, SGST, IGST, CESS, grand total.

---

## 5. Persistence & Audit

| Artifact | Rule |
|----------|------|
| Invoice lines | Product name, qty, rate, taxable, taxes, line total, extracted serial, match result |
| Additional products | Non-inventory lines attached to the invoice |
| XML archive | Compressed raw XML per voucher; admins may open original XML from the sale |
| Decision log | Per line: serial source, extracted/normalized serial, inventory id, GUID, match result, decision, reason, timestamp |
| Indexes | Voucher GUID, invoice number, serial, import date |

### Voucher status model

`Received` → `Parsed` → `Matched` → `Completed` | `Completed With Review Required` | `Failed` | `Skipped`

---

## 6. Scheduler & Restart

- Primary identity: **Voucher GUID** (Sales and New Sales).
- After office-server restart: resume from **last successful sync date** → current date.
- Filter duplicate GUIDs. No skipped invoices; no duplicate imports.

---

## 7. Duplicate Sale Detection

If the serial is already **`sold`** in IMS (Case E):

- Do not modify inventory.
- Do not create a duplicate sale.
- Mark line **Review Required** and notify (`duplicate_sale`).

---

## 8. Notifications (Version 1)

| Category | Trigger |
|----------|---------|
| Duplicate Sale | Case E |
| Product Model Mismatch | Case B (sale still applied) |
| Tally Sync Completed | Sync cycle imported invoices |
| Synchronization Failure | Repeated connection/sync failures |

---

## 9. Table Responsibilities

| Table | Purpose |
|-------|---------|
| `tally_processed_invoice` | Invoice-level state, totals, XML archive, GUID idempotency |
| `tally_processed_invoice_line` | Per-line outcomes, additional products, decision fields |
| `tally_line_decision_log` | Immutable per-line decision audit |
| `tally_sync_log` / `tally_sync_history` | Run diagnostics |

---

## 10. Sale Detail (API data)

Sale detail exposes: invoice number/date/time, imported date/time, voucher GUID, MasterID, customer, payment mode, tracked products (serial, model, rate, GST), additional products, invoice totals, review status, and whether original XML is available. UI styling is out of scope for this redesign.

---

## 11. Regression Requirements

Must cover: AES/0147 backpack (no-serial must not sell unrelated laptop), multiple serialized products, model mismatch + review, restart/GUID dedupe, XML archive, invoice totals, additional products, Case D/E.
