# WEBSTUDIO IMS — Flutter Mobile Client

Official mobile client for WEBSTUDIO IMS. Android is the primary target; the architecture is iOS-compatible.

This is **not** a companion app — it uses the same backend APIs and business rules as the desktop client.

## Stack

| Layer | Choice |
|-------|--------|
| UI | Flutter (stable), Material 3 |
| State | Riverpod |
| Navigation | GoRouter |
| HTTP | Dio (API envelope + JWT refresh) |
| Offline cache | Hive entity cache, pending ops, API cache, sync state |
| Secrets | Flutter Secure Storage |
| Media / scan | image_picker, camera, mobile_scanner, file_picker, share_plus, permission_handler, flutter_local_notifications |

## Prerequisites

1. [Flutter SDK](https://docs.flutter.dev/get-started/install) (stable channel)
2. Android Studio / SDK (primary)
3. Xcode (for iOS builds on macOS)
4. Running WEBSTUDIO backend (`http://127.0.0.1:8000` or LAN IP)

## First-time setup

```bash
cd apps/mobile_flutter
bash scripts/setup_platforms.sh   # generates android/ + ios/ if missing
flutter pub get
```

### API URL

| Environment | Default |
|-------------|---------|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator / desktop | `http://127.0.0.1:8000` |
| Physical device | Your PC's LAN IP, e.g. `http://192.168.1.100:8000` |

Configure from **More → Settings → API server** or the connection screen on first launch.

## Commands

```bash
# Analyze + unit tests
bash scripts/lint_and_test.sh

# Full mobile QA suite (analyze + all tests + QA summary)
bash scripts/mobile_qa.sh

# Run on Android emulator
flutter run

# Debug APK
bash scripts/build_android_debug.sh
```

## Project layout (feature-first)

```
lib/
  core/           # theme, routing, network, storage, config
  shared/         # cross-feature widgets
  features/
    auth/         # login, session bootstrap
    connection/   # server discovery
    dashboard/    # KPIs, distribution, recent activity
    inventory/    # hierarchy workspace, drawer, barcode scan
    sales/          # sales list, filters, detail sheet
    catalogue/      # brands, models, locations tabs
    reports/        # report center previews
    notifications/  # system alerts
    users/          # user directory
    settings/       # app + admin status
    backup/         # backup & recovery status + import
    media/          # product image capture/upload
    tally/          # tally integration status
    shell/        # bottom navigation shell
```

## Design parity

Colors, typography (Lato), spacing, and brand assets are aligned with `apps/desktop/src/index.css` and `public/assets/webstudio/`.

## Authentication flow

1. **Connection** — auto LAN discovery, manual URL, saved servers, health + setup test
2. **Bootstrap** — offline check → health → restore JWT from secure storage
3. **Login** — Remember Me (username only), lockout after 3 failures, status messages
4. **Session** — proactive refresh, idle logout, 401 retry (same as desktop)
5. GoRouter redirects unauthenticated users to login

See `docs/mobile/MILESTONE_10B_AUTH_CONNECTION_REPORT.md` for full details.

## Inventory & dashboard (10C)

1. **Dashboard** — live KPIs, location/brand bars, recent activity from `/api/v1/dashboard/*`
2. **Inventory** — brands → models → serials hierarchy matching desktop
3. **Detail sheet** — transfer (`inventory:transfer`) and mark sold (`sales:create`)
4. **Barcode scan** — camera scanner for Code 128/39, EAN, UPC, and desktop inventory QR codes

See `docs/mobile/MILESTONE_10C_DASHBOARD_INVENTORY_REPORT.md` for full details.

## Sales & catalogue (10D)

1. **Sales** — paginated list, filters, detail sheet (`sales:view`)
2. **Catalogue** — brands, models, locations tabs with search, sort, client pagination
3. **Workspace lookup** — sales/inventory lookup, barcode scan, add inventory, transfer

See `docs/mobile/MILESTONE_10D_SALES_CATALOGUE_REPORT.md` for full details.

## Reports & administration (10E)

1. **Reports** — inventory, sales, audit, tally previews from `/api/v1/reports/*`
2. **Notifications** — list, search, mark read, archive
3. **Users** — paginated directory with detail sheet
4. **Settings** — backup, recovery, tally, and AI provider status summaries
5. **Backup / Tally** — dedicated status screens using same APIs as desktop

See `docs/mobile/MILESTONE_10E_REPORTS_ADMIN_REPORT.md` for full details.

## Device integration (10F)

1. **Barcode** — expanded manufacturer formats; serial, model, and part number auto-detection
2. **Camera** — capture/upload/preview product images via `/api/v1/product-images/*`
3. **Files** — backup import, report download, and share
4. **Notifications** — local push architecture with background unread alerts
5. **Permissions** — camera, storage, and notifications in Settings

See `docs/mobile/MILESTONE_10F_DEVICE_INTEGRATION_REPORT.md` for full details.

## Offline architecture (10G)

1. **Hive cache** — inventory, dashboard, sync state, and pending operations
2. **Offline dashboard & inventory lookup** — cache-then-network with stale indicators
3. **Background sync** — `/api/v1/sync/state` polling, retry queue, conflict detection
4. **Pending mutations** — transfer and mark-sold queued when offline

See `docs/mobile/MILESTONE_10G_OFFLINE_ARCHITECTURE_REPORT.md` for full details.

## Mobile QA (10H)

Automated QA suite in `test/qa/` covering auth, inventory, sales, barcode, offline, sync, performance, memory, battery architecture, themes, and layouts.

```bash
bash scripts/mobile_qa.sh
```

See `docs/mobile/MILESTONE_10H_MOBILE_QA_REPORT.md` for full matrix and manual checklists.

## Enterprise parity (10I)

Desktop feature parity extensions: global search, audit center, Add Laptop wizard, inventory edit/archive/restore, continuous barcode scan (manufacturer only), Tally manual sync, user admin actions, adaptive `NavigationRail` tablet shell, and shared UX widgets.

```bash
bash scripts/mobile_qa.sh   # 67/67 tests
```

Reports:

- `docs/mobile/MILESTONE_10I_ENTERPRISE_MOBILE_COMPLETION_REPORT.md`
- `docs/mobile/MILESTONE_10I_DESKTOP_FEATURE_PARITY_REPORT.md`
- `docs/mobile/MILESTONE_10I_MOBILE_QA_REPORT.md`
- `docs/mobile/MILESTONE_10I_KNOWN_DIFFERENCES_REPORT.md`

## Production readiness (10J)

Final mobile completion: catalogue CRUD forms, sales timeline/audit/export, settings write panel, 7-step Add Laptop wizard, global search orchestrator, dashboard KPI extensions, product image delete, barcode sound/haptic prefs, and Sales tablet master-detail.

```bash
flutter analyze   # 0 errors
flutter test      # 69/69 tests
```

Reports:

- `docs/mobile/MILESTONE_10J_ENTERPRISE_MOBILE_COMPLETION_REPORT.md`
- `docs/mobile/MILESTONE_10J_DESKTOP_FEATURE_PARITY_REPORT.md`
- `docs/mobile/MILESTONE_10J_MOBILE_QA_REPORT.md`
- `docs/mobile/MILESTONE_10J_KNOWN_DIFFERENCES_REPORT.md`

## Related docs

- `docs/mobile/MILESTONE_10A_FLUTTER_FOUNDATION_REPORT.md`
- `docs/mobile/MILESTONE_10B_AUTH_CONNECTION_REPORT.md`
- `docs/mobile/MILESTONE_10C_DASHBOARD_INVENTORY_REPORT.md`
- `docs/mobile/MILESTONE_10D_SALES_CATALOGUE_REPORT.md`
- `docs/mobile/MILESTONE_10E_REPORTS_ADMIN_REPORT.md`
- `docs/mobile/MILESTONE_10F_DEVICE_INTEGRATION_REPORT.md`
- `docs/mobile/MILESTONE_10G_OFFLINE_ARCHITECTURE_REPORT.md`
- `docs/mobile/MILESTONE_10H_MOBILE_QA_REPORT.md`
- `docs/mobile/MILESTONE_10I_ENTERPRISE_MOBILE_COMPLETION_REPORT.md`
- `docs/mobile/MILESTONE_10I_DESKTOP_FEATURE_PARITY_REPORT.md`
- `docs/mobile/MILESTONE_10I_KNOWN_DIFFERENCES_REPORT.md`
- `docs/mobile/MILESTONE_10J_ENTERPRISE_MOBILE_COMPLETION_REPORT.md`
- `docs/mobile/MILESTONE_10J_DESKTOP_FEATURE_PARITY_REPORT.md`
- `docs/mobile/MILESTONE_10J_MOBILE_QA_REPORT.md`
- `docs/mobile/MILESTONE_10J_KNOWN_DIFFERENCES_REPORT.md`
- `docs/api/API_SPECIFICATION.md`
