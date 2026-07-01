---
Title: Milestone 10I — Known Differences
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
---

# Known Differences — Desktop vs Mobile

Intentional exclusions and technical justifications for Milestone 10I. Each item was reviewed against desktop modules.

---

## Intentionally excluded

### 1. Internal QR inventory labels

**Desktop:** Generates and scans JSON QR payloads for inventory items.

**Mobile:** Manufacturer barcodes only (Code128, Code39, EAN, UPC, ITF, Data Matrix). Internal QR parsing removed from `BarcodeFieldResolver` and scanner formats.

**Justification:** Milestone 10I spec explicitly prohibits internal QR. Warehouse staff use manufacturer serial labels; desktop QR is a print-shop workflow ill-suited to phone camera ergonomics.

---

### 2. Tally XML import, recovery, database restore

**Desktop:** Full recovery center with XML import and DB restore.

**Mobile:** Operational sync only (status, manual sync, retry, connection test).

**Justification:** High-risk administrative operations require large file uploads, multi-step validation, and desktop screen space. Mobile exposes read-only recovery dashboard link only via Settings where permitted.

---

### 3. Integration API key management

**Desktop:** Admin can create/rotate integration keys.

**Mobile:** Not exposed.

**Justification:** Secret rotation on mobile poses clipboard/leak risk; admin tasks remain desktop-only per security policy.

---

### 4. Saved filters (inventory, reports)

**Desktop:** Persists named filter presets per user.

**Mobile:** Session-level filters only.

**Justification:** Requires new sync schema for filter presets; deferred to avoid scope creep. Users can re-apply common filters via search.

---

### 5. Sales audit timeline & per-sale export

**Desktop:** Full sale lifecycle audit and direct invoice PDF.

**Mobile:** Sale detail read view; export via Reports module.

**Justification:** Sale audit API exists but desktop drawer UX does not map cleanly to mobile bottom sheets; reports cover export use case.

---

### 6. Master-detail tablet layouts per module

**Desktop:** Split pane inventory/catalogue on wide screens.

**Mobile:** `NavigationRail` at shell level only; module screens remain single-column lists.

**Justification:** Prevents stretched phone UI. Full master-detail per module is Milestone 11+ enhancement.

---

### 7. Product image delete

**Desktop:** Can remove product model image.

**Mobile:** Upload/replace/AI fetch only.

**Justification:** Delete endpoint exists but low mobile priority; accidental delete risk on touch UI.

---

## Backend / API limitations

### 8. Global search: customer & invoice

**10I spec requested:** Search customers and invoices.

**Backend `global_search_service`:** Returns `inventory`, `brand`, `location`, `product_model` only.

**Mobile:** Wired to existing API. Customer/invoice search requires backend extension — not a mobile-only gap.

---

### 9. Global search: part number as distinct type

**Mobile:** Part numbers resolved via barcode heuristics and inventory hierarchy search, not a separate search result type.

**Justification:** Backend indexes models/inventory; part numbers map to model numbers in practice.

---

## Partial implementations (documented gaps)

| Gap | Reason | Path forward |
|-----|--------|--------------|
| Catalogue brand/location/model forms | Repo complete; UI is browse-first | Add edit sheets in 11 |
| User create/edit forms | Admin API wired; no form UI | Add wizard in 11 |
| Settings write panels | PATCH paths in `ApiPaths`; read UI from 10E | Permission-gated forms in 11 |
| AI spec refresh in catalogue | Repo only | Hook to model detail sheet |
| Offline cache for sales/catalogue | Keys defined in `OfflineCacheKeys` | Wire services like 10G inventory |
| Manual sync progress UI | Background coordinator handles queue | Expose progress in offline banner |

---

## Platform constraints

| Constraint | Impact |
|------------|--------|
| No Android SDK / incomplete Xcode on dev Mac | Automated tests pass; camera/scan needs emulator or device |
| `mobile_scanner` 6.x | Continuous scan uses detection cooldown; very fast scans may need debounce tuning on device |
| Hive cache size | Very large inventories rely on API pagination + selective cache (10G design) |

---

## RBAC

All new write surfaces (inventory archive, user admin, tally sync) check the same permission strings as desktop. Features hidden when permission absent — no client-side bypass.

---

## Sign-off

These differences are **accepted for Milestone 10I review**. Revisit in Milestone 11 planning for master-detail tablet layouts, catalogue CRUD forms, and backend global search expansion.
