---
Title: Milestone 10A — Flutter Foundation & Architecture
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/api/MILESTONE_9C_MOBILE_READINESS_REPORT.md
---

# Milestone 10A — Flutter Foundation & Architecture

## Summary

Milestone 10A establishes the **official WEBSTUDIO IMS Flutter mobile client** at `apps/mobile_flutter/`. This is a full mobile client using the same backend — not a companion app. Android is primary; iOS compatibility is built into project structure, secure storage options, and platform-aware API client headers.

The legacy React Native stub in `apps/mobile/` is unchanged; Flutter is the forward path for mobile development.

---

## Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Flutter project | ✅ | `apps/mobile_flutter/` |
| Feature-first module layout | ✅ | `lib/features/*`, `lib/core/*`, `lib/shared/*` |
| Material 3 theme (desktop parity) | ✅ | `lib/core/theme/` |
| GoRouter navigation + shell | ✅ | `lib/core/routing/`, `lib/features/shell/` |
| Auth bootstrap | ✅ | `lib/bootstrap.dart`, `lib/features/auth/` |
| Dio API client (envelope + JWT refresh) | ✅ | `lib/core/network/api_client.dart` |
| Secure token storage | ✅ | `lib/core/storage/secure_token_storage.dart` |
| Hive offline cache | ✅ | `lib/core/storage/hive_cache.dart` |
| Connection / server discovery | ✅ | `lib/features/connection/` |
| Feature module shells (12 modules) | ✅ | Placeholder screens per module |
| Lint configuration | ✅ | `analysis_options.yaml`, `flutter_lints` |
| Unit / widget tests | ✅ | `test/` (4 test files) |
| Build scripts | ✅ | `scripts/setup_platforms.sh`, `build_android_debug.sh` |
| Documentation | ✅ | `README.md`, this report |

---

## Architecture

### Feature modules

| Module | Milestone 10A scope |
|--------|---------------------|
| **Authentication** | Login, JWT restore, refresh, logout |
| **Connection** | Health probe, URL persistence, auto-discovery |
| **Dashboard** | Shell + `GET /api/v1/sync/state` preview |
| **Inventory** | Placeholder (barcode/camera in 10B+) |
| **Sales** | Placeholder |
| **Catalogue** | Placeholder |
| **Reports** | Placeholder |
| **Notifications** | Placeholder |
| **Users** | Placeholder |
| **Settings** | Theme mode, API URL, sign out |
| **Backup** | Placeholder |
| **Tally** | Placeholder |
| **Shared** | Logo, loading, feature placeholders |
| **Shell** | Bottom navigation (5 tabs) |

### State management

- **Riverpod** for app config, auth session, theme mode, API client, router
- **ProviderContainer** bootstrapped in `main.dart` with secure storage + shared preferences overrides

### Networking

- Reuses backend contract: `/api/v1/*` paths, success `data` envelope, error `error` envelope
- Headers: `X-Client-Platform` (`android_mobile` / `ios_mobile`), `X-Client-Version`
- 401 interceptor → refresh token → retry (mirrors desktop `RetryingApiClient`)
- No duplicated business logic — validation and workflows remain server-side

### Offline

- **Hive** boxes: `sync_state`, `profile_cache`, `settings_cache`
- Dashboard reads cached sync state when network unavailable

### Security

- JWT access + refresh tokens in **Flutter Secure Storage** (Android encrypted shared prefs, iOS keychain)
- Key names aligned with desktop `AuthTokenStore`

---

## Design language

Matched to desktop (`apps/desktop/src/index.css`):

| Token | Light | Dark |
|-------|-------|------|
| App background | `#EEF1F6` | `#0F1419` |
| Surface | `#FFFFFF` | `#161B22` |
| Primary | `#2B4C7E` | `#5B8FCE` |
| Brand navy / coral | `#1A2F52` / `#E8684A` | same |
| Body font | Lato 13px via `google_fonts` | same |
| Radius scale | 6 / 10 / 14 / 18 px | same |

Brand assets copied from `apps/desktop/public/assets/webstudio/`.

---

## Navigation map

```
/bootstrap → health + session restore
/connection → manual / auto server discovery
/login → credentials
/dashboard  ┐
/inventory  │
/sales      ├─ StatefulShell (bottom nav)
/catalogue  │
/more       ┘
  /more/reports
  /more/notifications
  /more/users
  /more/settings
  /more/backup
  /more/tally
```

GoRouter `redirect` enforces auth gates identically to desktop flow (connection → login → workspace).

---

## Dependencies (pubspec)

| Package | Purpose |
|---------|---------|
| flutter_riverpod | State |
| go_router | Navigation |
| dio | HTTP |
| hive / hive_flutter | Offline cache |
| flutter_secure_storage | JWT |
| google_fonts | Lato typography |
| flutter_svg | Brand logo |
| image_picker, camera, mobile_scanner | Declared for inventory milestones |
| connectivity_plus, package_info_plus, shared_preferences | Platform utilities |

---

## Test plan

| Test | File |
|------|------|
| API error envelope parsing | `test/core/errors/api_exception_test.dart` |
| Auth model JSON | `test/features/auth/auth_models_test.dart` |
| Theme Material 3 | `test/core/theme/app_theme_test.dart` |
| Config defaults | `test/core/config/app_config_test.dart` |

### Run locally (requires Flutter SDK)

```bash
cd apps/mobile_flutter
bash scripts/lint_and_test.sh
bash scripts/build_android_debug.sh   # after setup_platforms.sh
```

**Verification (2026-06-27):** `flutter analyze` — no issues. `flutter test` — 6/6 passed.

---

## Platform setup

Platform folders (`android/`, `ios/`) are generated on demand:

```bash
bash scripts/setup_platforms.sh
```

Uses `flutter create --org com.webstudio --project-name webstudio_ims .`

---

## Parity with desktop

| Concern | Desktop | Mobile (10A) |
|---------|---------|--------------|
| Login payload | `device_label: WEBSTUDIO Desktop` | `device_label: WEBSTUDIO Mobile` |
| Token storage | Electron secure storage / localStorage | Flutter Secure Storage |
| API base URL | ConfigService + ConnectionPage | SharedPreferences + ConnectionScreen |
| Theme | light / dark / system | light / dark / system |
| Business logic | Backend only | Backend only ✅ |

---

## Out of scope (future milestones)

- Full inventory CRUD, barcode scanning UI
- Sales workflow screens
- Catalogue management
- Push notifications
- Biometric unlock
- Delta sync / offline writes
- iOS App Store / Play Store release pipelines

---

## Review checklist

- [ ] Install Flutter stable and run `scripts/setup_platforms.sh`
- [ ] `bash scripts/lint_and_test.sh` passes
- [ ] Launch against local backend; complete login
- [ ] Verify theme toggle in Settings
- [ ] Confirm sync state tile on Dashboard after auth
- [ ] Approve feature-first structure for 10B implementation

---

## Files added

Primary path: `apps/mobile_flutter/` (~45 Dart source files, 4 tests, scripts, assets)

Monorepo scripts (recommended addition to root `package.json`):

```json
"mobile:flutter:setup": "cd apps/mobile_flutter && bash scripts/setup_platforms.sh",
"mobile:flutter:test": "cd apps/mobile_flutter && bash scripts/lint_and_test.sh"
```

---

**Status: STOPPED FOR REVIEW** per milestone instructions.
