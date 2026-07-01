---
Title: Milestone 10D — Sales & Catalogue
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10C_DASHBOARD_INVENTORY_REPORT.md
---

# Milestone 10D — Sales & Catalogue

## Summary

Milestone 10D delivers the mobile Sales workspace and Catalogue manager with desktop parity for list/search/filter/pagination/sort behavior, plus a shared workspace lookup sheet for sales lookup, inventory lookup, barcode scan, add inventory, and transfer.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Sales list | ✅ | `sales_screen.dart` — server-paginated list (50/page) |
| Sales details | ✅ | `sales_detail_sheet.dart` — invoice, customer, laptop, Tally |
| Catalogue brands | ✅ | Brands tab with stock counts, archive/restore |
| Catalogue models | ✅ | Models tab (mobile addition; desktop manages via Inventory) |
| Catalogue locations | ✅ | Locations tab with type and stock |
| Search | ✅ | Toolbar search on Sales + Catalogue |
| Filters | ✅ | `sales_filters_sheet.dart` — date, brand, store, salesperson, etc. |
| Pagination | ✅ | Server-side (Sales 50/page), client-side (Catalogue 25/page) |
| Sorting | ✅ | Sales via API sort fields; Catalogue client-side sort menu |
| Add inventory | ✅ | `workspace_lookup_sheet.dart` — `POST /api/v1/inventory` |
| Transfer | ✅ | Lookup sheet — serial → location dialog |
| Sales lookup | ✅ | Lookup sheet — `GET /api/v1/sales?search=` |
| Inventory lookup | ✅ | Lookup sheet — `GET /api/v1/inventory/by-serial/{serial}` |
| Barcode search | ✅ | Reuses `BarcodeScannerScreen` from 10C |
| Tests | ✅ | `sales_models_test.dart` + existing suite (15 total) |

---

## Sales workspace

Mirrors desktop `useSalesWorkspace`:

- **API:** `GET /api/v1/sales`, `GET /api/v1/sales/{id}`
- **Default sort:** `sold_at` desc
- **Filters:** brand, location, salesperson (derived from results), invoice, customer, payment mode, sale source, date range
- **Search:** debounced 300ms → `search` query param
- **Detail drawer:** invoice, customer, laptop specs, Tally sync info when `sale_source=tally`
- **Permission:** `sales:view` (backend enforced)

---

## Catalogue workspace

Three tabs (Brands · Models · Locations):

| Tab | Data source | Pagination | Sort |
|-----|-------------|------------|------|
| Brands | `GET /api/v1/brands` | Client 25/page | name, display order, models, available |
| Models | `GET /api/v1/product-models` | Client 25/page | model number, name, brand, status |
| Locations | `GET /api/v1/locations` | Client 25/page | name, type, stock, capacity |

Stock counts enriched from `GET /api/v1/dashboard/distribution`.

**Write actions** (permission-gated via `canWriteCatalogue`):
- Create brand / location
- Archive / restore brand / location

---

## Workspace lookup sheet

Shared bottom sheet available from Sales, Catalogue, and Inventory toolbars:

| Action | Permission | API |
|--------|------------|-----|
| Sales lookup | `sales:view` | `GET /api/v1/sales?search=` |
| Inventory lookup | `inventory:view` | `GET /api/v1/inventory/by-serial/{serial}` |
| Barcode scan | — | Camera + `BarcodeFieldResolver` |
| Add inventory | `inventory:create` | `POST /api/v1/inventory` |
| Transfer | `inventory:transfer` | `PATCH /api/v1/inventory/{id}/location` |

---

## File map

```
lib/features/sales/
  domain/sales_models.dart
  data/sales_repository.dart
  presentation/sales_controller.dart
  presentation/sales_screen.dart
  presentation/widgets/sales_detail_sheet.dart
  presentation/widgets/sales_filters_sheet.dart

lib/features/catalogue/
  domain/catalogue_models.dart
  data/catalogue_repository.dart
  presentation/catalogue_controller.dart
  presentation/catalogue_screen.dart

lib/shared/widgets/workspace_lookup_sheet.dart

test/features/sales/sales_models_test.dart
```

---

## Verification

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
# flutter analyze — clean
# flutter test — 15/15 passing
```

**Manual smoke test checklist:**

1. Sales → search invoice, apply filters, paginate, open sale detail
2. Catalogue → switch tabs, search, sort, paginate, include archived
3. Create brand and location (if permissions allow)
4. Lookup → sales search opens sale detail from Sales tab
5. Lookup → inventory serial opens detail from Inventory tab
6. Lookup → add inventory unit with model + location
7. Lookup → transfer unit by serial

---

## Known gaps (future milestones)

| Item | Notes |
|------|-------|
| Sales export | Desktop `sales:export` → XLSX not on mobile yet |
| Catalogue CSV export | Desktop client-side export |
| Brand/location edit forms | Mobile supports create + archive/restore only |
| Location archive transfer preview | Desktop `archive-preview` flow simplified |
| Sales audit timeline | Desktop drawer loads audit logs |
| Full add-laptop wizard | Desktop multi-step model creation wizard |

---

## Desktop impact

**None.** Mobile consumes existing APIs only.
