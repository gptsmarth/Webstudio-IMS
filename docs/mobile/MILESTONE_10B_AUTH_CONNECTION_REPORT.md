---
Title: Milestone 10B — Authentication & Server Connection
Version: 0.1.0
Status: Ready for Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/mobile/MILESTONE_10A_FLUTTER_FOUNDATION_REPORT.md
---

# Milestone 10B — Authentication & Server Connection

## Summary

Milestone 10B implements the full mobile authentication and server connection flow, aligned with the desktop `ConnectionPage` and `LoginPage` behavior. The Flutter app now supports LAN discovery, manual server entry, saved servers, connection testing, login with Remember Me, JWT refresh, session restoration, idle logout, and offline handling.

---

## Deliverables

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Server URL configuration | ✅ | `AppConfigController.setApiBaseUrl`, Settings + Login server chip |
| LAN server discovery | ✅ | `ConnectionController.startAutoDiscovery` (desktop candidate URLs + saved servers) |
| Manual server entry | ✅ | Connection manual form |
| Saved servers | ✅ | `ServerPreferences` (up to 8, recency-ordered) |
| Connection testing | ✅ | `ServerRepository.testConnection` — `/health/live` + `/api/v1/setup/status` |
| Login | ✅ | `AuthController.login` → same API payload as desktop |
| Remember Me | ✅ | Username only in `SharedPreferences` (never password) |
| Refresh token | ✅ | Dio 401 interceptor + `SessionManager` proactive refresh |
| Session restoration | ✅ | `AuthRepository.restoreSession` on bootstrap |
| Logout | ✅ | Server + local token clear |
| Session expiry | ✅ | Idle timeout + failed refresh → `AuthStatus.sessionExpired` |
| Desktop-like login UX | ✅ | Brand gradient panel, outlets, status messages, lockout |
| Dark / Light mode | ✅ | Login app-bar toggle + Settings segmented control |
| Offline handling | ✅ | `OfflineBanner` + bootstrap connectivity check |
| Loading states | ✅ | Searching / testing / authenticating spinners + status text |

---

## Connection flow

Matches desktop `ConnectionPage` state machine:

```
searching → found → bootstrap
         ↘ manual → testing → found | manual (error)
```

**Discovery candidates** (same as desktop + Android emulator):

- `http://10.0.2.2:8000` (Android emulator)
- `http://127.0.0.1:8000`
- `http://localhost:8000`
- `http://192.168.1.100:8000`
- `http://192.168.1.1:8000`
- Previously saved servers

**Connection test** validates:

1. `GET /health/live` — server reachable
2. `GET /api/v1/setup/status` — WEBSTUDIO API (returns company name when initialized)
3. Optional `GET /api/v1/version` — backend version in result

Successful connections are saved with company name as label when available.

---

## Authentication flow

```
/bootstrap
  ├─ offline? → /connection
  ├─ health fail? → /connection
  └─ restoreSession()
       ├─ refresh if access token expired
       ├─ GET /api/v1/auth/me
       └─ authenticated → /dashboard | unauthenticated → /login

/login
  ├─ load saved username if Remember Me
  ├─ POST /api/v1/auth/login (device_label: WEBSTUDIO Mobile)
  ├─ GET /api/v1/auth/me (permissions merge)
  └─ save/clear username per Remember Me

Authenticated shell
  ├─ SessionManager: idle logout per session-policy
  ├─ SessionManager: proactive refresh <60s to expiry
  └─ OfflineBanner when connectivity lost
```

**Parity with desktop:**

| Behavior | Desktop | Mobile |
|----------|---------|--------|
| Remember Me | `saved_username` only | `saved_username` + `remember_me` flags |
| Failed login lockout | 3 attempts → 30s | Same |
| Login status messages | Verifying / Establishing session | Same |
| Refresh on 401 | `RetryingApiClient` | Dio interceptor |
| Idle logout | `useSessionManager` | `SessionManager` widget |

---

## Key files

| Path | Purpose |
|------|---------|
| `lib/features/connection/presentation/connection_screen.dart` | Desktop-style connection UI |
| `lib/features/connection/presentation/connection_controller.dart` | Discovery state machine |
| `lib/features/connection/data/server_repository.dart` | Test + discover + persist |
| `lib/features/connection/data/server_preferences.dart` | Saved servers + Remember Me |
| `lib/features/auth/presentation/login_screen.dart` | Login UI |
| `lib/features/auth/presentation/auth_controller.dart` | Auth state + lockout |
| `lib/features/auth/presentation/session_manager.dart` | Idle + proactive refresh |
| `lib/features/auth/presentation/bootstrap_screen.dart` | Startup + offline |
| `lib/shared/widgets/offline_banner.dart` | Offline indicator |
| `lib/shared/widgets/startup_shell.dart` | Brand panel layout |

---

## Tests

| Test file | Coverage |
|-----------|----------|
| `test/features/connection/server_preferences_test.dart` | Saved servers, Remember Me |
| `test/features/auth/auth_controller_test.dart` | Lockout countdown |
| Existing 10A tests | Theme, models, API envelope, config |

**Results:** `flutter analyze` — no issues · `flutter test` — **9/9 passed**

---

## Manual test plan

1. Launch app with backend stopped → connection screen after bootstrap
2. Tap **Retry automatic discovery** with backend on `127.0.0.1:8000` (or `10.0.2.2` on emulator)
3. Confirm server appears in **Saved servers** after success
4. Sign in with Remember Me → kill app → relaunch → username prefilled
5. Sign out from Settings → returns to login
6. Wait for idle timeout (or shorten `session_timeout_minutes` in DB) → session expired message
7. Toggle dark mode on login screen
8. Enable airplane mode while authenticated → offline banner visible

---

## Out of scope (future milestones)

- Password recovery via recovery key (desktop has slide-over panel)
- Setup wizard for uninitialized systems
- Biometric unlock
- Certificate pinning

---

**Status: STOPPED FOR REVIEW**
