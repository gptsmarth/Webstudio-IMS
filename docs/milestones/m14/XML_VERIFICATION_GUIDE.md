---
Title: Tally XML Verification Guide
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14C
Related Documents:
  - docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md
  - tools/scripts/uat_analyze_tally_xml.py
  - docs/integrations/tally-erp9/TALLY_SYNC_ENGINE_ARCHITECTURE.md
---

# Tally XML Verification Guide (M14C)

How to verify **Tally XML request generation** and **response parsing** during production commissioning.

---

## 1. XML request structure

WEBSTUDIO generates export requests via `TallyXmlClient._export_request()`:

| Element | Purpose |
|---------|---------|
| `TALLYREQUEST` | `Export` |
| `TYPE` | `Data` |
| `ID` | `Vouchers` |
| `SVCURRENTCOMPANY` | Configured company name |
| `VOUCHERTYPENAME` | `Sales` or `NEW SALE` |
| `SVFROMDATE` / `SVTODATE` | `YYYYMMDD` incremental window |
| `SVEXPORTFORMAT` | `$$SysName:XML` |

**Production validation** checks this template via the `xml_request_generation` check in:

```http
GET /api/v1/integrations/tally/production-validation
```

---

## 2. Capturing live XML from Tally

### Option A — Connection test (minimal)

`POST /api/v1/integrations/tally/connection/test` confirms Tally responds to a minimal export envelope. Does not return voucher data.

### Option B — Manual curl (engineer, on server LAN)

Replace host, company, and dates:

```bash
curl -s -X POST "http://LENOVO-TALLY:9000" \
  -H "Content-Type: text/xml" \
  --data-binary @- <<'EOF'
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
        <SVCURRENTCOMPANY>YOUR COMPANY NAME</SVCURRENTCOMPANY>
        <VOUCHERTYPENAME>Sales</VOUCHERTYPENAME>
        <SVFROMDATE>20260701</SVFROMDATE>
        <SVTODATE>20260702</SVTODATE>
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
EOF
```

Save response to `tally-export-sample.xml` (handle confidential data per store policy).

### Option C — Analyze script (read-only)

```bash
python tools/scripts/uat_analyze_tally_xml.py path/to/tally-export-sample.xml
```

Reports voucher counts, serial extraction, laptop line detection — **no database writes**.

---

## 3. Required voucher fields

Each `VOUCHER` in the response must include:

| Field | WEBSTUDIO use |
|-------|---------------|
| `GUID` | Primary deduplication key |
| `MASTERID` | Secondary metadata |
| `VOUCHERTYPENAME` | Must be monitored type |
| `VOUCHERNUMBER` | Display / fallback fingerprint |
| `DATE` | `YYYYMMDD` |
| `PARTYLEDGERNAME` | Customer |
| `REFERENCE` or printed invoice | Staff-visible invoice number |
| `ALLINVENTORYENTRIES.LIST` | Line items |
| `SERIALNUMBER` or `BASICUSERDESCRIPTION` | IMEI / serial matching |

**Verify parsing:**

```python
from webstudio_backend.integrations.tally.xml_parser import parse_vouchers_xml
vouchers = parse_vouchers_xml(open("sample.xml").read())
assert vouchers[0].guid
```

Unit fixtures: `apps/backend/tests/tally/fixtures/sample_vouchers.py`

---

## 4. Incremental window verification

1. Record `last_successful_sync_at` from dashboard or API.
2. Inspect generated request dates — `SVFROMDATE` should equal last sync **date** (not full history).
3. After import, confirm `last_imported_voucher_date` and `last_processed_guid` advanced.

Helper:

```python
from webstudio_backend.integrations.tally.incremental_sync import resolve_incremental_from_date
# company_sync loaded from DB
from_date = resolve_incremental_from_date(company_sync)
```

---

## 5. Duplicate GUID verification

1. Run successful sync (note GUID from `tally_processed_invoice` or audit).
2. Trigger **Sync now** again without new Tally vouchers.
3. **Pass:** `invoices_skipped` increases; no duplicate sales; `duplicates` counter may increment for serial collisions only.

---

## 6. XML error handling

| Response symptom | `connectivity_status` | Action |
|------------------|----------------------|--------|
| Empty body | `xml_error` | Company name mismatch; books closed |
| Connection refused | `offline` | Start Tally / check port |
| Malformed XML | `xml_error` | Re-export; check Tally version |
| HTTP error | `offline` | Firewall / hostname |

Sync history records `offline` or `failed` with `error_summary` — never silent drop.

---

## 7. What staff must not see

Per product policy, **GUID, MasterID, AlterID, and raw XML** are admin/engineer diagnostics only. Dashboard and mobile surfaces show business fields only.

---

## 8. Checklist cross-reference

| XML topic | Checklist ID |
|-----------|--------------|
| Request template | TLY-05 |
| Live response | TLY-05a, TLY-05b |
| Incremental dates | TLY-06 |
| GUID checkpoint | TLY-07 |
| Duplicate skip | TLY-12 |

Complete [TALLY_VALIDATION_CHECKLIST.md](TALLY_VALIDATION_CHECKLIST.md) after XML verification.
