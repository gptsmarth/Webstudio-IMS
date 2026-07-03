---
Title: Tally Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Tally Guide

Operator guide for **Tally ERP 9** integration with WEBSTUDIO IMS.

---

## 1. Overview

WEBSTUDIO imports **Sales** and **NEW SALE** vouchers from Tally and matches serial numbers to inventory.

| Direction | Data flow |
|-----------|-----------|
| Tally → WEBSTUDIO | Invoices, serials, customer, payment mode |
| WEBSTUDIO → Tally | **None** (read-only integration) |

---

## 2. Prerequisites

- Tally ERP 9 running on billing PC during business hours
- XML interface port **9000** enabled
- Company books open in Tally
- Serial numbers on voucher lines (SERIALNUMBER or BASICUSERDESCRIPTION)
- Server can reach Tally hostname on LAN

---

## 3. Administrator setup

**Settings → Tally:**

| Field | Example |
|-------|---------|
| Enable | On |
| Host | `tally-laptop` (hostname, not IP) |
| Port | `9000` |
| Company | Exact Tally company name |
| Interval | `300` seconds (5 min) |

**Test Connection** must succeed before relying on auto-sync.

Server env: `WEBSTUDIO_TALLY_SCHEDULER=1`

---

## 4. What staff see

| Metric | Meaning |
|--------|---------|
| **Last Sync** | Last successful import run |
| **Last Invoice** | Printed invoice number (REFERENCE) |
| **Last Invoice Date** | Voucher date |
| **Next Sync** | Scheduled poll time |
| **Imported Today / Week / Month** | Count of new imports |
| **Sync Health** | Healthy / Needs attention / Offline |

**Hidden from everyone:** GUID, MasterID, AlterID, raw XML.

---

## 5. Daily operation

1. Open Tally on billing PC at start of day
2. Process sales as normal in Tally
3. WEBSTUDIO syncs automatically — inventory moves to **SOLD**
4. Check **Sync Health** if sales missing in WEBSTUDIO

---

## 6. Duplicate protection

- Same Tally invoice imported once (GUID dedup)
- Re-sync skips already-imported vouchers
- Duplicate sale notifications if serial already sold

---

## 7. Common issues

| Symptom | Fix |
|---------|-----|
| Offline | Tally PC off or wrong hostname |
| Missing serial | Add serial in Tally; ensure item in WEBSTUDIO as Available |
| Model mismatch warning | Informational — serial is authoritative |
| No imports today | First sync imports today only; check voucher date |

---

## 8. Manual sync

**Settings → Tally → Sync now** (admin) or wait for next scheduled run.

---

## 9. Detailed references

| Document | Audience |
|----------|----------|
| [M12E Deployment](../m12e/TALLY_DEPLOYMENT_GUIDE.md) | IT installer |
| [M12E Validation](../m12e/VALIDATION_GUIDE.md) | Go-live checklist |
| [M12E Recovery](../m12e/RECOVERY_GUIDE.md) | Outages |
| [XML Developer Guide](../../integrations/tally-erp9/xml-developer-guide.md) | Engineers only |
