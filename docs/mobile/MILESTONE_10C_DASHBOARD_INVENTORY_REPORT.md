---
Title: Milestone 10C — Dashboard & Inventory
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10B_AUTH_CONNECTION_REPORT.md
---

# Milestone 10C — Dashboard & Inventory

## Summary

Milestone 10C delivers the mobile dashboard and full inventory workspace with desktop parity for hierarchy navigation, search, filters, status display, transfer, mark sold, and camera barcode scanning. Desktop workflows are unchanged; mobile adds hardware barcode scanning not present on desktop.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Dashboard | ✅ | `dashboard_screen.dart` — KPIs, location/brand distribution, recent activity |
| Inventory workspace | ✅ | Brands → models → serials drill-down (`inventory_screen.dart`) |
| Inventory drawer | ✅ | `inventory_detail_sheet.dart` — specs, status, transfer, mark sold |
| Search | ✅ | Toolbar search with field picker (all / serial / model / brand) |
| Filters | ✅ | Status, location, color filters (`inventory_filters_sheet.dart`) |
| Grouping | ✅ | `inventory_hierarchy.dart` — same brand/model grouping as desktop |
| Status | ✅ | `InventoryStatusChip` — received, available, reserved, sold + archived |
| Transfer | ✅ | `PATCH /api/v1/inventory/{id}/location` via detail sheet dialog |
| Mark sold | ✅ | `PATCH /api/v1/inventory/{id}/mark-sold` with desktop fields |
| Barcode scanner | ✅ | `barcode_scanner_screen.dart` — `mobile_scanner` camera UI |
| Code 128 / 39 / EAN / UPC | ✅ | Scanner format list + `BarcodeFieldResolver` heuristics |
| Auto field population | ✅ | Serial, model number, part number from scan result |
| Tests | ✅ | Barcode resolver + hierarchy unit tests (13 total app tests) |

---

## Dashboard

Uses the same APIs as desktop:

- `GET /api/v1/dashboard` — operations snapshot (units, value, outlets)
- `GET /api/v1/dashboard/distribution` — by location and brand
- `GET /api/v1/dashboard/recent-activity` — latest inventory events

`dashboardDataProvider` loads all three in parallel on screen open.

---

## Inventory workspace

Mirrors desktop `useInventoryHierarchyData` flow:

```
Brands (with per-location counts)
  → Models (in-stock / include zero-stock toggle)
    → Serials (filtered list)
      → Detail sheet (drawer)
```

**Data sources:**

| Data | API |
|------|-----|
| Brands | `GET /api/v1/brands` |
| Product models | `GET /api/v1/product-models` |
| Locations | `GET /api/v1/locations` |
| Inventory items | `GET /api/v1/inventory` (paginated fetch-all) |
| Distribution | `GET /api/v1/dashboard/distribution` |
| Lookup by serial | `GET /api/v1/inventory/by-serial/{serial}` |

**Actions** (permission-gated, same as desktop):

| Action | Permission | API |
|--------|------------|-----|
| Transfer | `inventory:transfer` | `PATCH /api/v1/inventory/{id}/location` |
| Mark sold | `sales:create` | `PATCH /api/v1/inventory/{id}/mark-sold` |

Mark sold dialog fields: invoice number, customer name, payment mode (Cash, Card, UPI, Bank Transfer, Finance), sale date, amount, remarks.

---

## Barcode scanning

Mobile-only feature using `mobile_scanner` with camera permission on Android (`CAMERA`) and iOS (`NSCameraUsageDescription`).

**Supported symbologies:** Code 128, Code 39, EAN-8/13, UPC-A/E, QR (desktop inventory QR JSON).

**Field resolution** (`barcode_field_resolver.dart`):

1. Desktop inventory QR JSON → serial number (+ optional inventory ID)
2. EAN/UPC numeric codes → model or part number by length
3. Model-number pattern (e.g. `XPS-15`) → model number
4. Manufacturer part pattern (uppercase alphanumeric) → part number
5. Default → serial number

Scan from inventory toolbar: opens item by serial when QR/serial matches, otherwise applies search term to the active field.

---

## File map

```
lib/features/dashboard/
  data/dashboard_repository.dart
  domain/dashboard_models.dart
  presentation/dashboard_screen.dart

lib/features/inventory/
  data/inventory_repository.dart
  domain/inventory_models.dart
  domain/inventory_hierarchy.dart
  domain/barcode_field_resolver.dart
  domain/inventory_permissions.dart
  presentation/inventory_controller.dart
  presentation/inventory_screen.dart
  presentation/barcode_scanner_screen.dart
  presentation/widgets/
    inventory_detail_sheet.dart
    inventory_filters_sheet.dart
    inventory_action_dialogs.dart
    inventory_status_chip.dart

test/features/inventory/
  barcode_field_resolver_test.dart
  inventory_hierarchy_test.dart
```

---

## Verification

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
# flutter analyze — clean (info-level deprecations only)
# flutter test — 13/13 passing
```

**Manual smoke test checklist:**

1. Login → Dashboard loads metrics and activity
2. Inventory → drill brands → models → serials
3. Search and filter serials by status/location/color
4. Open serial detail sheet → transfer to another location
5. Mark available unit sold with payment details
6. Scan desktop-generated inventory QR → navigates to serial
7. Scan EAN barcode → search populates model field

---

## Known gaps (future milestones)

| Item | Notes |
|------|-------|
| Audit timeline in drawer | Desktop drawer shows full audit log |
| Archive / restore | Not in mobile UI yet |
| Global search API | `GET /api/v1/search` not wired; client-side + by-serial lookup used |
| Sibling units / lifecycle stepper | Desktop drawer extras |
| Paginated reference data | Brands/locations/models fetch first page only (sufficient for typical deployments) |

---

## Desktop impact

**None.** No changes to `apps/desktop/` or backend APIs. Mobile consumes existing `/api/v1/*` endpoints only.
