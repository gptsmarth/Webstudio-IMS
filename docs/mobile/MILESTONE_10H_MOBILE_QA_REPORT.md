---
Title: Milestone 10H — Mobile QA
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10G_OFFLINE_ARCHITECTURE_REPORT.md
---

# Milestone 10H — Mobile QA

## Summary

Milestone 10H establishes automated mobile QA coverage across authentication, inventory, sales, barcode, offline, synchronization, performance, memory, themes, and layout scenarios. A dedicated QA test suite and `scripts/mobile_qa.sh` runner were added. Battery profiling on physical hardware remains a documented manual checklist.

---

## QA execution

```bash
cd apps/mobile_flutter
bash scripts/mobile_qa.sh
```

| Step | Result |
|------|--------|
| `flutter analyze` | ✅ No issues |
| Unit tests (`test/`) | ✅ 31 regression tests |
| QA suite (`test/qa/`) | ✅ 36 QA tests |
| **Total** | **✅ 67/67 passing** |

---

## Test matrix

| Area | Automated | Tests | Notes |
|------|-----------|-------|-------|
| Authentication | ✅ | 4 | User/tokens parsing, lockout, session states |
| Inventory | ✅ | 4 | Search, filters, mark-sold payload, hierarchy |
| Sales | ✅ | 3 | Sale detail, filter query params, pagination |
| Barcode | ✅ | 5 | QR, EAN, Code39, format list, scan registry |
| Offline | ✅ | 4 | Cache keys, stale flags, pending ops |
| Synchronization | ✅ | 3 | Conflict detection, high-water marks, JSON round-trip |
| Performance | ✅ | 3 | 1000-item hierarchy &lt;200ms, 5000-row pagination |
| Memory | ✅ | 3 | JSON round-trip, bounded fixtures (10k items) |
| Battery usage | ✅ | 2 | Poll interval clamp (30–300s architecture guard) |
| Dark mode | ✅ | 1 | Dark `ThemeData` brightness |
| Light mode | ✅ | 2 | Light theme + mode switch widget |
| Phone layout | ✅ | 1 | 390×844 NavigationBar scaffold |
| Tablet layout | ✅ | 1 | 1024×768 NavigationRail + expanded body |
| Large dataset | ✅ | 3 | 1000 inventory, 5000 catalogue rows, 10k memory fixture |

---

## Authentication testing

| Scenario | Coverage |
|----------|----------|
| Login payload parsing | `AuthUser.fromJson`, `AuthTokens.fromJson` |
| Display label / permissions | QA auth tests |
| Lockout after 3 failures | `AuthState.isLockedOut`, countdown |
| Session expired vs unauthenticated | Status enum distinction |
| Offline cached session | Implemented in 10G (`readCachedUser`) — manual device QA recommended |

**Manual device checklist:** login, remember-me, logout, token refresh, idle logout, offline bootstrap.

---

## Inventory testing

| Scenario | Coverage |
|----------|----------|
| Serial search | `matchesSerialSearch` |
| Filter query params | `InventoryListFilters.toQueryParams` |
| Mark sold desktop parity | `MarkSoldRequest.toJson` |
| Brand hierarchy aggregation | `buildBrandSummaries` with archived brand exclusion |
| Transfer / detail sheet | Manual on device (permission-gated) |

---

## Sales testing

| Scenario | Coverage |
|----------|----------|
| Sale detail parsing | Full `SaleDetail.fromJson` field set |
| Filter + sort API params | `SalesListFilters.toQueryParams` |
| Client pagination | `paginateItems` with 250 rows |

---

## Barcode testing

| Scenario | Coverage |
|----------|----------|
| Desktop inventory QR | Serial + inventory ID extraction |
| EAN-13 → model number | Resolver heuristic |
| Manufacturer Code39 | Part number pattern |
| Supported symbologies | `supportedBarcodeFormats` list |
| Future scan sources | `ScanInputRegistry` implemented vs planned |

**Manual device checklist:** camera permission, torch toggle, live scan → inventory search.

---

## Offline testing

| Scenario | Coverage |
|----------|----------|
| Cache key namespacing | `OfflineCacheKeys` |
| Stale cache detection | `CachedPayload.isOlderThan`, `OfflineLoadResult` |
| Pending operation enqueue | `PendingOperationFactory` |
| Offline dashboard / inventory | Service layer in 10G — manual airplane-mode QA |

**Manual device checklist:** airplane mode → dashboard shows cache banner; serial lookup from cache; transfer queues pending op.

---

## Synchronization testing

| Scenario | Coverage |
|----------|----------|
| Conflict on `updated_at` mismatch | `ConflictDetector` |
| High-water mark change detection | `SyncStateSnapshot.hasEntityChanges` |
| Pending op serialization | JSON round-trip |
| Auto-sync on reconnect | `OfflineBanner` listener — manual QA |

---

## Performance testing

| Benchmark | Threshold | Measured (CI) |
|-----------|-----------|---------------|
| `buildBrandSummaries` × 1000 items | &lt;200ms | Pass |
| `paginateItems` page 100 of 5000 | &lt;50ms | Pass |
| Serial scan 1000 cached items | &lt;100ms | Pass |

---

## Memory testing

| Scenario | Coverage |
|----------|----------|
| Item JSON round-trip | No data loss across 20 items |
| Pagination immutability | Source list unchanged |
| Large fixture uniqueness | 10,000 unique serials |

**Manual device checklist:** DevTools memory snapshot after loading full inventory workspace.

---

## Battery usage

| Check | Type |
|-------|------|
| Sync poll clamp 30–300s | Automated architecture guard |
| No tight polling loops | Automated |
| Background camera / scanner idle | Manual — verify scanner disposes on pop |
| Sync coordinator timer | Manual — profile on Android with battery historian |

---

## Dark / light mode

| Mode | Automated |
|------|-----------|
| Light | Material 3, primary color scheme |
| Dark | `Brightness.dark` verification |
| System switch | `ThemeMode.system` widget build |

**Manual device checklist:** Settings → Theme segmented control on device.

---

## Phone / tablet layout

| Layout | Viewport | Verification |
|--------|----------|--------------|
| Phone | 390×844 | `NavigationBar` bottom nav |
| Tablet | 1024×768 | `NavigationRail` + full-width scaffold |

Current production shell uses bottom `NavigationBar` on all form factors; tablet rail pattern validated as layout-ready in QA widgets. Adaptive shell enhancement deferred.

---

## Large dataset testing

| Dataset | Size | Test |
|---------|------|------|
| Inventory items | 1,000 | Hierarchy build performance |
| Catalogue rows | 5,000 | Pagination slice |
| Memory fixture | 10,000 | Unique serial integrity |

---

## Files added

```
test/qa/
  qa_fixtures.dart
  auth_qa_test.dart
  inventory_qa_test.dart
  sales_qa_test.dart
  barcode_qa_test.dart
  offline_qa_test.dart
  sync_qa_test.dart
  performance_qa_test.dart
  memory_qa_test.dart
  battery_qa_test.dart
  layout_qa_test.dart
scripts/mobile_qa.sh
```

---

## Known gaps (manual QA recommended before release)

1. End-to-end integration tests against live backend (deferred — unit/QA only)
2. Widget/integration tests for full screen flows (login → inventory drill-down)
3. Physical device battery profiling (Android Battery Historian / Xcode Energy Log)
4. Camera/barcode hardware on real devices
5. Adaptive tablet shell (NavigationRail) not yet in production `MainShell`

---

## Ready for review

Milestone 10H is complete pending review. All automated QA checks pass (`67/67`).
