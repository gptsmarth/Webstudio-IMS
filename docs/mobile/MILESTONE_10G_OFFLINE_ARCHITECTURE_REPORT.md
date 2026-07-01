---
Title: Milestone 10G — Offline Architecture
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10F_DEVICE_INTEGRATION_REPORT.md
---

# Milestone 10G — Offline Architecture

## Summary

Milestone 10G prepares the Flutter mobile client for offline work with Hive entity caching, API response persistence, background synchronization against `/api/v1/sync/state`, conflict detection on replay, a retry queue for pending mutations, and connectivity-aware UI. Dashboard and inventory lookup operate from cache when the network is unavailable.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Hive cache | ✅ | Expanded `HiveCache` — entity, pending ops, API cache boxes |
| API caching | ✅ | `OfflineCacheStore` + `ApiCacheService` |
| Background synchronization | ✅ | `BackgroundSyncCoordinator` polls sync state + refreshes caches |
| Conflict detection | ✅ | `ConflictDetector` compares `updated_at` on replay |
| Retry queue | ✅ | `RetryQueue` processes pending ops (max 3 attempts) |
| Pending operations | ✅ | `PendingOperationsStore` + `PendingOperationFactory` |
| Connectivity detection | ✅ | `connectivityProvider` + reconnect auto-sync in `OfflineBanner` |
| Offline inventory lookup | ✅ | `OfflineInventoryService.lookupBySerial()` |
| Offline dashboard | ✅ | `OfflineDashboardService.loadDashboard()` |
| Automatic synchronization | ✅ | Poll timer + connectivity restore trigger |
| Tests | ✅ | Conflict detector + pending operation tests (30 total) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ UI: Dashboard, Inventory, OfflineBanner, Workspace Lookup   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│ OfflineInventoryService / OfflineDashboardService            │
│   cache-then-network reads, stale flags                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌───────────────┐  ┌────────────────┐  ┌──────────────────────┐
│ Hive entity   │  │ Pending ops    │  │ SyncStateRepository  │
│ cache boxes   │  │ + RetryQueue   │  │ GET /sync/state      │
└───────────────┘  └────────────────┘  └──────────────────────┘
                            │
                            ▼
                   BackgroundSyncCoordinator
                   (poll + reconnect + replay)
```

---

## Hive boxes

| Box | Purpose |
|-----|---------|
| `entity_cache` | Inventory brands/models/locations/items, dashboard snapshot |
| `pending_operations` | Queued transfer / mark-sold / create mutations |
| `api_cache` | Raw API response bodies (extensible) |
| `sync_state` | Latest server sync token + high-water marks |
| `profile_cache` | Cached user profile for offline session (10B) |

---

## Offline reads

### Dashboard

`OfflineDashboardService.loadDashboard()`:

1. When online — fetch `/api/v1/dashboard`, `/distribution`, `/recent-activity`; persist to Hive.
2. On network failure or offline — serve last cached bundle with `isStale: true`.
3. UI shows cached-data banner on `DashboardScreen`.

### Inventory

`OfflineInventoryService.loadWorkspace()` caches brands, models, locations, distribution, and all inventory items after each successful online fetch.

`lookupBySerial(serial)` searches the cached item list first; falls back to `GET /inventory/by-serial/{serial}` when online.

---

## Pending operations & retry

When offline, inventory mutations are queued instead of failing:

| Mutation | Pending type | Replay |
|----------|--------------|--------|
| Transfer location | `transferLocation` | `PATCH /inventory/{id}/location` |
| Mark sold | `markSold` | `PATCH /inventory/{id}/mark-sold` |
| Create inventory | `createInventory` | `POST /inventory` |

`RetryQueue.processAll()` runs on sync. Before applying a mutation, `ConflictDetector` compares the server's `updated_at` with the snapshot captured at enqueue time. Mismatches mark the operation with a `SyncConflict` for review.

---

## Background synchronization

`BackgroundSyncCoordinator`:

1. Starts when the main shell mounts (`OfflineBanner`).
2. Fetches `GET /api/v1/sync/state` and compares `high_water_marks` to the last local snapshot.
3. Replays the retry queue when online.
4. Refreshes inventory + dashboard caches when entity watermarks change or ops were applied.
5. Schedules the next poll using `poll_interval_seconds` from the server (30–300s clamp).
6. Re-runs immediately when connectivity returns from offline.

---

## Connectivity & session

| Signal | Source | Behavior |
|--------|--------|----------|
| Network interface | `connectivity_plus` | Offline banner, cache-only reads |
| Server sync state | `/api/v1/sync/state` | Change detection baseline |
| Cached session | `HiveCache.profile` | Bootstrap allows offline entry with cached user |

---

## New modules

```
lib/core/offline/
  offline_models.dart
  offline_cache_store.dart
  api_cache_service.dart
  sync_state_repository.dart
  conflict_detector.dart
  pending_operations_store.dart
  pending_operation_factory.dart
  retry_queue.dart
  offline_inventory_service.dart
  offline_dashboard_service.dart
  offline_providers.dart
```

---

## Deferred / out of scope

- Per-entity delta endpoints (backend `incremental_sync.status: preparation`)
- Full offline sales / catalogue / reports workspaces
- Conflict resolution UI (conflicts surfaced via sync banner count)
- Workmanager / isolate background sync when app is killed
- Server reachability probing beyond sync-state fetch

---

## Verification

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
```

---

## Ready for review

Milestone 10G is complete pending review. Offline dashboard and inventory lookup are functional with automatic sync when connectivity returns.
