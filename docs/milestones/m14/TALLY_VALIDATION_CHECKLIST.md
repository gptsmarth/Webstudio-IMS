---
Title: Tally Validation Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14C
Related Documents:
  - docs/milestones/m14/TALLY_PRODUCTION_GUIDE.md
  - docs/milestones/m14/XML_VERIFICATION_GUIDE.md
  - docs/milestones/m14/TALLY_VALIDATION_REPORT.md
---

# Tally Validation Checklist (M14C)

Complete during production commissioning. **Assume live Tally is running** on the billing PC unless noted.

Mark each item **Pass / Fail / N/A** and attach evidence.

---

## A. Configuration

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| TLY-01 | Tally ERP 9 running | Company books open on billing PC | Screenshot |
| TLY-02 | XML port enabled | TCP **9000** accepts connections locally | `telnet localhost 9000` or Tally config |
| TLY-03 | Server resolves hostname | Server can reach `tally_host` on LAN | `ping` / Test Connection |
| TLY-04 | Settings configured | Enable, host, port, company, interval saved | Settings screenshot |
| TLY-04a | Test Connection | API returns reachable=true | Connection test JSON |
| TLY-04b | Scheduler env | `WEBSTUDIO_TALLY_SCHEDULER=1` on server | `.env` excerpt |
| TLY-04c | Probe env | `WEBSTUDIO_TALLY_CONNECTIVITY_PROBE=1` | `.env` excerpt |

---

## B. XML and import pipeline

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| TLY-05 | XML request generation | Export template contains company, voucher type, date range | `xml_request_generation` check passed |
| TLY-05a | Live XML response | Tally returns voucher XML for Sales / NEW SALE | Saved XML sample (redact PII) |
| TLY-05b | Parser | `parse_vouchers_xml` extracts GUID, serial, amount | XML Verification Guide §3 |
| TLY-06 | Incremental sync | Second sync does not re-import full history | Sync history: invoices_checked stable |
| TLY-07 | GUID checkpoint | `last_processed_guid` updates after import | DB query or validation API |
| TLY-08 | Last sync timestamp | Dashboard **Last Sync** matches DB | Dashboard screenshot |

---

## C. Resilience

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| TLY-09 | Server restart recovery | After service restart, auto sync resumes within 1 interval | Service restart log + history |
| TLY-10 | Tally restart recovery | After Tally close/open, sync resumes | Tally restart test notes |
| TLY-11 | Offline replay | Vouchers created while Tally offline import when back | Offline test procedure §D |
| TLY-12 | Duplicate prevention | Re-sync skips same GUID; `duplicates` counter stable | Manual re-sync test |

---

## D. Offline replay procedure

1. Note current `last_successful_sync_at` on dashboard.
2. Create a test Sales voucher in Tally **while sync is paused** (stop Tally or disconnect network briefly).
3. Restore Tally connectivity.
4. Trigger **Sync now** or wait for scheduler.
5. **Pass:** Voucher appears in WEBSTUDIO; history shows successful run (not full re-import of old data).

---

## E. Manual and automatic sync

| ID | Check | Pass criteria | Evidence |
|----|-------|---------------|----------|
| TLY-13 | Manual sync | Sync now queues run; history shows new entry | POST trigger or UI |
| TLY-14 | Automatic scheduler | Sync runs without user action within interval | History timestamp |
| TLY-15 | Polling interval | Setting `tally_sync_interval_seconds` respected (60–3600) | Settings + next sync time |
| TLY-16 | Dashboard status | Sync health, last/next sync, imports today visible | Dashboard / Tally page |

---

## F. Automated validation

```http
GET /api/v1/integrations/tally/production-validation
```

**Pass:** `overall_status` is `passed` or `warning` with documented remediation (no `failed` for go-live).

```powershell
.\infra\windows\validate-production-tally.ps1 -BearerToken "<jwt>" -TallyHost "<hostname>"
```

---

## G. Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Accounts (Tally) | | | |
| Store administrator | | | |
| WEBSTUDIO engineer | | | |

**Overall result:** ☐ Pass — Tally production ready &nbsp; ☐ Fail — remediate before go-live

---

## H. Failure escalation

| Symptom | First action |
|---------|--------------|
| Test Connection fails | Verify Tally running, port 9000, hostname |
| Sync health offline | Check billing PC power and LAN |
| Missing serials | Add serial in Tally; item must be Available in WEBSTUDIO |
| Duplicates in notifications | Expected for already-sold serials — verify GUID dedup in history |

See [TALLY_PRODUCTION_GUIDE.md](TALLY_PRODUCTION_GUIDE.md) §7–8.
