---
Title: Tally XML Developer Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12E
Related Documents:
  - docs/integrations/tally-erp9/incremental-sync-engine.md
  - docs/integrations/tally-erp9/sync-strategy.md
---

# Tally XML Developer Guide

**Audience:** Backend engineers and integration developers only.  
**Not for application UI** — operators never see raw XML, GUID, MasterID, or AlterID.

WEBSTUDIO IMS uses Tally ERP 9’s HTTP XML interface on port **9000** (default). This guide documents the exact requests, sample responses, and field mapping used by the production sync engine (migration `0034`).

---

## Transport

| Item | Value |
|------|-------|
| Method | `POST` |
| URL | `http://{host}:{port}/` |
| Content-Type | `text/xml` |
| Timeout | 60 seconds (configurable) |

Implementation: `integrations/tally/xml_client.py`

---

## 1. Connection test request

Used by connectivity probes and the Settings → Test Connection action.

### Exact XML request

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Connection Test</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>
```

### Sample response (truncated)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <STATUS>1</STATUS>
  </HEADER>
  <BODY>
    <DATA>
      <COLLECTION>...</COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>
```

### Explanation

| Element | Purpose |
|---------|---------|
| `TALLYREQUEST` | Must be `Export` for read operations |
| `TYPE` | `Data` for voucher export |
| `SVEXPORTFORMAT` | Forces XML output (`$$SysName:XML`) |
| Non-empty body | Any parseable XML indicates Tally is listening |

---

## 2. Incremental voucher export request

Production sync exports **Sales** and **NEW SALE** voucher types for a **date window** from `last_successful_sync_at` through today. GUID deduplication happens server-side after parse.

### Exact XML request

Replace `{COMPANY}`, `{VOUCHER_TYPE}`, `{FROM_YYYYMMDD}`, `{TO_YYYYMMDD}`:

```xml
<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>Vouchers</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
        <SVCURRENTCOMPANY>{COMPANY}</SVCURRENTCOMPANY>
        <VOUCHERTYPENAME>{VOUCHER_TYPE}</VOUCHERTYPENAME>
        <SVFROMDATE TYPE="Date">{FROM_YYYYMMDD}</SVFROMDATE>
        <SVTODATE TYPE="Date">{TO_YYYYMMDD}</SVTODATE>
      </STATICVARIABLES>
    </DESC>
    <DATA>
      <TALLYMESSAGE>
        <COLLECTION NAME="Vouchers">
          <TYPE>Voucher</TYPE>
        </COLLECTION>
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
```

**Example** — company `WEBSTUDIO`, Sales vouchers, 27 Jun–2 Jul 2026:

- `SVCURRENTCOMPANY`: `WEBSTUDIO`
- `VOUCHERTYPENAME`: `Sales`
- `SVFROMDATE`: `20260627`
- `SVTODATE`: `20260702`

Monitored voucher types: `Sales`, `NEW SALE` (see `integrations/tally/constants.py`).

**Tally Prime:** use **Day Book** export (`<ID>Day Book</ID>`) — the legacy `Vouchers` collection returns empty/error on Tally Prime. WEBSTUDIO filters Sales / NEW SALE server-side after parse.

**Date variables must carry `TYPE="Date"`** (`<SVFROMDATE TYPE="Date">20260601</SVFROMDATE>`) — without the attribute several Tally builds silently ignore the period and export only the current date, which breaks historical backfills while appearing to work for same-day syncs.

**Historical backfill fallback:** when a ranged Day Book export returns no `<VOUCHER>` elements — or when Day Book itself returns `<LINEERROR>` / `<STATUS>0</STATUS>` — the client retries with the period-based **Voucher Register** report (`<TALLYREQUEST>Export Data</TALLYREQUEST>` + `<REPORTNAME>Voucher Register</REPORTNAME>`), which returns all voucher types (Sales and Purchase) and reliably honours `SVFROMDATE`/`SVTODATE` on both ERP 9 and Prime. Only if the register also fails does the client fall back to per-type collection exports for `Sales`, `NEW SALE`, `Purchase`, and `NEW PURCHASE`. All three paths are read-only exports.

---

## 3. Sample XML response

From test fixture `tests/tally/fixtures/sample_vouchers.py`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
  <BODY>
    <DATA>
      <TALLYMESSAGE>
        <VOUCHER>
          <GUID>a1b2c3d4-e5f6-7890-abcd-ef1234567890</GUID>
          <MASTERID>10001</MASTERID>
          <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
          <VOUCHERNUMBER>42</VOUCHERNUMBER>
          <REFERENCE>WEB/24-25/00042</REFERENCE>
          <DATE>20240615</DATE>
          <PARTYLEDGERNAME>Walk-in Customer</PARTYLEDGERNAME>
          <NARRATION>Retail sale</NARRATION>
          <ALLINVENTORYENTRIES.LIST>
            <STOCKITEMNAME>ASUS Vivobook X1502ZA</STOCKITEMNAME>
            <ACTUALQTY>1 Nos</ACTUALQTY>
            <BATCHALLOCATIONS.LIST>
              <SERIALNUMBER>SN-TALLY-001</SERIALNUMBER>
            </BATCHALLOCATIONS.LIST>
          </ALLINVENTORYENTRIES.LIST>
        </VOUCHER>
      </TALLYMESSAGE>
    </DATA>
  </BODY>
</ENVELOPE>
```

---

## 4. XML field reference

| XML element | Internal use | Exposed to UI/API |
|-------------|--------------|-------------------|
| `GUID` | Primary dedup key (`tally_processed_invoice.tally_voucher_guid`) | **Never** |
| `MASTERID` | Stored for traceability only | **Never** |
| `ALTERID` | Not used in v1 engine | **Never** |
| `VOUCHERTYPENAME` | Store mapping (`Sales` → location) | Voucher type label only |
| `VOUCHERNUMBER` | Internal Tally number | Internal voucher (Sales detail) |
| `REFERENCE` | Printed invoice number | **Last Invoice** / printed invoice |
| `DATE` | Voucher date (`YYYYMMDD`) | **Last Invoice Date** |
| `PARTYLEDGERNAME` | Customer name + fallback fingerprint | Customer name |
| `STOCKITEMNAME` | Model matching | — |
| `SERIALNUMBER` / `BASICUSERDESCRIPTION` | Inventory serial lookup | Serial on sale record |
| `AMOUNT` / `RATE` (inventory line) | Selling price on sale record | **Sale amount** (Sales workspace) |
| `NARRATION` | Optional context | — |

Parser: `integrations/tally/xml_parser.py`

---

## 5. Incremental behaviour (developer)

| Scenario | Fetch window | Dedup |
|----------|--------------|-------|
| First successful sync | Today only | GUID + fingerprint |
| After success | From `last_successful_sync_at.date()` | GUID skips already-imported |
| Weekend / holiday gap | From last sync date through today | Re-fetch window; DB skips known GUIDs |
| Tally offline | No fetch; watermark unchanged | Retry next poll |
| Partial line failure | Same window re-fetched | Completed lines skipped via `tally_processed_invoice_line` |
| Server restart | Scheduler resumes from `scheduler_runtime_state.next_run_at` | Stale `sync_in_progress` cleared on startup |

Helper: `integrations/tally/incremental_sync.py` → `resolve_incremental_from_date()`

---

## 6. Error handling

| Condition | HTTP / XML | Engine action |
|-----------|------------|---------------|
| Tally not running | Connection refused | Connectivity status `offline`; retry |
| Wrong company name | Empty or error body | Logged; sync run `failed` |
| Malformed XML | Parse exception | Run `failed`; no watermark advance |
| Duplicate GUID in batch | Parser `seen_guids` | Second copy dropped in same response |

User-facing messages: `integrations/tally/connectivity.py` → `map_exception_to_user_message()`

---

## 7. Key modules

| Module | Responsibility |
|--------|----------------|
| `xml_client.py` | Build export envelopes; HTTP POST |
| `xml_parser.py` | Parse vouchers and inventory lines |
| `incremental_sync.py` | Date window, interval clamp, fingerprints |
| `tally_sync_service.py` | Orchestration, dedup, sales creation |
| `tally_dashboard_service.py` | User-safe operational DTO |

---

## 8. Security note

GUID, MasterID, and AlterID are **internal database keys**. They must not appear in:

- REST API responses (Tally dashboard, sync history, sales detail)
- Desktop or mobile UI
- CSV exports shown to operators

Audit and server logs may reference voucher numbers and printed invoices for support; never expose raw GUID in operator-facing surfaces.
