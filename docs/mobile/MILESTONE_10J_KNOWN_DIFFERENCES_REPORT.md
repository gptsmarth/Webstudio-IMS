---
Title: Milestone 10J — Known Differences
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10I_KNOWN_DIFFERENCES_REPORT.md
---

# Known Differences — Desktop vs Mobile (Milestone 10J)

Only **intentional exclusions** and **documented technical limitations** remain. All 10I "Partial" items with no justification have been addressed in 10J unless listed below.

---

## Intentionally excluded (desktop-only)

### 1. Internal QR inventory labels

**Desktop:** Generates and scans JSON QR payloads.

**Mobile:** Manufacturer barcodes only.

**Justification:** Milestone spec prohibits internal QR on mobile. Warehouse workflow uses manufacturer labels.

---

### 2. Database restore, disaster recovery, server installation

**Desktop:** Full recovery center, DB restore, OS deployment wizards.

**Mobile:** Not exposed.

**Justification:** High-risk administrative operations require desktop screen space, file system access, and multi-step validation unsuitable for phone form factors.

---

### 3. Integration API key create / rotate

**Desktop:** Admin creates and rotates integration keys.

**Mobile:** **Read-only list** when `integration_keys:manage` permission present.

**Justification:** Secret rotation on mobile poses clipboard and shoulder-surfing risk. Admin key lifecycle remains desktop-only per security policy.

---

### 4. Saved filter presets

**Desktop:** Named filter presets persisted per user.

**Mobile:** Session-level filters only.

**Justification:** Requires user-preference sync schema not in v1.0 mobile scope. Search + filter sheets cover common workflows.

---

## Backend / API limitations (not mobile-only gaps)

### 5. Global search: customers and invoices as distinct result types

**Spec requested:** Dedicated customer and invoice search hits.

**Backend `global_search_service`:** Indexes inventory, brand, location, product_model only.

**Mobile mitigation:** `GlobalSearchOrchestrator` fans out to Sales API (invoice/customer fields), Audit, Notifications, and Users APIs. Full parity requires backend search index extension.

---

### 6. Dashboard today's sales / revenue time-series

**Desktop:** Live KPI widgets with intraday aggregates.

**Mobile:** Uses dashboard snapshot + distribution API. Intraday revenue KPIs need a dedicated mobile dashboard endpoint or aggregation layer.

**Justification:** Avoid duplicating business logic in the client; defer to backend KPI API in a future release.

---

## Remaining partial implementations (with justification)

| Item | Status | Justification |
|------|--------|---------------|
| Inventory/catalogue tablet master-detail | ⚠️ | Sales split layout shipped; inventory/catalogue use bottom sheets to avoid hierarchical nav complexity in v1.0 |
| User create/edit forms | ⚠️ | Admin lifecycle actions (reset/unlock/archive) complete; full user wizard low frequency on mobile |
| Settings security granular PATCH | ⚠️ | Read + company/Tally/AI writes shipped; password policy fields rarely changed from mobile |
| Sales trend chart on dashboard | ⚠️ | Distribution bars provided; chart widget needs design + data contract |
| Offline cache for sales/catalogue lists | ⚠️ | Cache keys defined; full offline browse deferred — inventory offline remains priority |
| `integration_test` E2E suite | ⚠️ | Unit/QA coverage at 69 tests; E2E planned for Milestone 11 |
| Manual device validation | ⚠️ | Camera/barcode require physical hardware; documented in QA report |

---

## Resolved from 10I (no longer partial)

| 10I gap | 10J resolution |
|---------|----------------|
| Catalogue CRUD UI | `catalogue_form_sheets.dart` + screen actions |
| Settings write panels | `settings_write_panel.dart` |
| Sales audit timeline | `sales_detail_sheet.dart` |
| Sales export | Sales screen export menu |
| Product image delete | Image sheet remove action |
| AI spec refresh in catalogue | Model form + wizard |
| Add Laptop desktop flow | 7-step wizard |
| Global search multi-source | `global_search_orchestrator.dart` |
| Barcode sound/haptic toggles | `barcode_scan_preferences.dart` |
| Tablet master-detail | `AdaptiveMasterDetail` on Sales |

---

## Platform constraints

| Constraint | Impact |
|------------|--------|
| `mobile_scanner` 6.x | Continuous scan cooldown; tune on device if needed |
| Hive cache size | Large inventories use API pagination + selective cache |
| iOS 15.5 minimum | Required by `mobile_scanner` pod |

---

## RBAC

All write surfaces introduced in 10J check the same permission strings as desktop. Features are hidden when permission is absent.

---

## Sign-off

These differences are **accepted for Milestone 10J review**. No undocumented "Partial" implementations remain for v1.0 mobile except those listed above with explicit justification.
