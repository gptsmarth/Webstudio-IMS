---
Title: Tally Sync Configuration Report
Version: 1.1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-10
Related Documents:
  - docs/integrations/tally-erp9/sync-strategy.md
  - docs/integrations/tally-erp9/TALLY_SYNC_VALIDATION_REPORT.md
  - docs/integrations/tally-erp9/TALLY_SYNC_ROOT_CAUSE_ANALYSIS.md
---

# Tally Sync Configuration Report

**Scope:** Document the redesigned deterministic Tally synchronization engine as implemented in source.  
**Environment note:** Live Tally ERP and the production backend run on **WEBSTUDIO-SERVER**. This report describes **code configuration**, not a live probe of the office workstation.

---

## 1. Current Engine

| Property | Value |
|----------|-------|
| Engine | Deterministic serial-only matching |
| Strategy doc | `docs/integrations/tally-erp9/sync-strategy.md` v1.3.0 |
| Service | `apps/backend/src/webstudio_backend/services/tally_sync_service.py` |
| Parser | `apps/backend/src/webstudio_backend/integrations/tally/xml_parser.py` |
| Client | `apps/backend/src/webstudio_backend/integrations/tally/xml_client.py` |
| Migration | `database/migrations/versions/0047_tally_sync_redesign.py` (+ `0048` refinement, `0049` GUID watermark) |
| Unsafe matching | **Removed** — no `_match_inventory_by_model`, no `models_equivalent`, no fuzzy/brand/token inventory selection |

**Invariant:** Inventory moves only on exact normalized serial match to exactly one `AVAILABLE` unit.

---

## 2. XML Request

Primary export (Tally Prime): **Day Book** (full voucher XML; filtered server-side by voucher type).

Fallback (if Day Book returns `LINEERROR`): per-type **Vouchers** collection export for each monitored type.

### Day Book request (template)

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Day Book</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>
        <SVFROMDATE>{YYYYMMDD}</SVFROMDATE>
        <SVTODATE>{YYYYMMDD}</SVTODATE>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>
```

| Setting | Source |
|---------|--------|
| Transport | HTTP POST `text/xml` to `http://{tally_host}:{tally_port}` |
| Company | System setting `tally_company_name` |
| From date | `resolve_incremental_from_date()` — prefers `last_imported_voucher_date`, else last successful sync / 30-day lookback |
| To date | Current date |

---

## 3. Voucher Types

| Monitored type | Store mapping |
|----------------|---------------|
| `Sales` | WEBSTUDIO |
| `NEW SALE` | AES |

Defined in `integrations/tally/constants.py` as `MONITORED_VOUCHER_TYPES` / `VOUCHER_TYPE_STORE_MAP`.

Other voucher types are ignored by the sync loop.

---

## 4. Polling Interval

| Setting | Default | Clamp |
|---------|---------|-------|
| `tally_sync_interval_seconds` | **300** (5 minutes) | 60–3600 seconds |

Registry default: `settings_registry.py`. Runtime clamp: `clamp_sync_interval_seconds()`.

---

## 5. Scheduler

| Component | Behaviour |
|-----------|-----------|
| Loop | `_tally_scheduler_loop()` in `app.py` |
| Env flag | `WEBSTUDIO_TALLY_SCHEDULER` (default true) |
| Runtime key | `tally_sync` in `scheduler_runtime_state` |
| Connectivity probe | Optional `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE` |
| Offline | Sync skipped; checkpoint preserved; resumes when Tally reachable |

Scheduler must be validated on the **office server** process (NSSM / Windows service), not on a developer laptop.

---

## 6. GUID Checkpoint & Watermark Optimization

| Field | Table | Role |
|-------|-------|------|
| `tally_voucher_guid` | `tally_processed_invoice` | **Primary idempotency key** (sole sync identity) |
| `last_processed_guid` | `tally_company_sync` | GUID watermark cursor (efficiency + diagnostics) |
| `last_processed_master_id` | `tally_company_sync` | Audit / diagnostics only |
| `last_processed_invoice_number` | `tally_company_sync` | Audit / diagnostics only — **never** used for identity |
| `last_processed_voucher_type` | `tally_company_sync` | Audit / diagnostics (`Sales` / `NEW SALE`) |
| `last_imported_voucher_date` | `tally_company_sync` | Incremental Day Book From-date |
| `last_successful_sync_at` | `tally_company_sync` | Restart / health / last successful sync |

Terminal statuses (`SUCCESS`, `COMPLETED_WITH_REVIEW_REQUIRED`, `SKIPPED`) cause the GUID to be skipped on re-fetch. Invoice numbers and MasterID are **not** used for synchronization identity.

### How the GUID watermark works

Tally’s XML API exports by **date range only** (no reliable “vouchers after GUID” API). The engine therefore still requests:

```text
FROM = last_imported_voucher_date
TO   = today
```

for monitored types (`Sales`, `NEW SALE`). XML download size is unchanged.

After parse + chronological sort `(voucher_date, guid)`:

1. Locate stored `last_processed_guid` in the batch.
2. If found: vouchers **at or before** that GUID are treated as already known — counted as watermark skips (no matching, no inventory work, no per-voucher run logs).
3. Vouchers **after** the watermark receive the full processing path, including GUID idempotency (`_should_skip_voucher`).
4. If the watermark GUID is **missing** from the batch: process the full list (safe fallback; GUID idempotency prevents duplicates).

After every successful synchronization, checkpoint fields above are persisted on `tally_company_sync`.

### Restart behaviour

Office server shutdown overnight → on restart the scheduler reads `last_imported_voucher_date` + `last_processed_guid`, requests the same date window, fast-skips via watermark, then fully processes only newer GUIDs. No invoice is skipped; no invoice is imported twice.

### Main Admin diagnostics

Dashboard `operational.sync_checkpoint` exposes:

- Last Imported Voucher Date  
- Last Processed GUID  
- Last Processed Master ID  
- Last Processed Voucher Type  
- Last Printed Invoice Number  
- Last Successful Sync  
- Current Scheduler State  

These values are diagnostics only and live under `sync_checkpoint` (not scattered as top-level public keys).

---

## 7. Matching Flow (Cases A–E)

```text
Extract serial (see §8)
        │
        ▼
 Exact normalized serial search in IMS
        │
   ┌────┴────────────────────────────────────────────┐
   │ No serial / not in IMS → Additional Product (C) │
   │ Duplicate IMS rows → Review, no sell (D)        │
   │ Already SOLD → Review, no sell (E)              │
   │ Not AVAILABLE → Review, no sell                 │
   │ AVAILABLE + model OK → Sale (A)                 │
   │ AVAILABLE + model differs → Sale + Review (B)   │
   └─────────────────────────────────────────────────┘
```

Model names never select inventory. Model comparison is verification-only after serial match.

---

## 8. Parser Flow

Serial extraction priority (production WEBSTUDIO XML):

1. `BASICUSERDESCRIPTION.LIST` → **first** `BASICUSERDESCRIPTION` only  
2. Direct `SERIALNUMBER`  
3. `BATCHALLOCATIONS.LIST` / `SERIALNUMBER`

Normalize for compare: trim + uppercase. Original value retained.  
Do **not** regex-scan remarks. Second+ `BASICUSERDESCRIPTION` entries are ignored (warranty text, etc.).

Amounts/taxes: read from XML only — **no GST ×1.18 estimation**.

---

## 9. Persistence & Audit

| Artifact | Purpose |
|----------|---------|
| `tally_processed_invoice` | Totals, GUID, status, gzip XML archive |
| `tally_processed_invoice_line` | Line amounts, serial, match/decision, additional products |
| `tally_line_decision_log` | Immutable per-line decision audit |
| `sales` | Review fields + voucher GUID/MasterID |

Each voucher processes inside a **nested DB transaction**. Failure rolls back inventory/sale for that voucher.

---

## 10. Sale Detail API (data only)

`GET /api/v1/sales/{id}` exposes GUID, MasterID, review fields, additional products, invoice totals, `original_xml_available`.  
`GET /api/v1/sales/{id}/original-xml` (Main Admin) returns archived XML.

No UI styling changes in this redesign.

---

## 11. Server configuration checklist (run on WEBSTUDIO-SERVER)

Confirm on the office server `.env` / settings UI:

- [ ] `tally_enabled=true`
- [ ] `tally_host` / `tally_port` reach the Tally workstation
- [ ] `tally_company_name` matches the live company
- [ ] `tally_sync_interval_seconds` in 60–3600
- [ ] `WEBSTUDIO_TALLY_SCHEDULER=1`
- [ ] Migration `0047_tally_sync_redesign` / `0048_tally_sync_refinement` / `0049_tally_guid_watermark` applied
- [ ] Backend service restarted after deploy

Live values must be read from the server — they are not certified from this developer machine.
