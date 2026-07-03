---
Title: Client Deployment Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14E
Related Documents:
  - docs/milestones/m14/DESKTOP_DEPLOYMENT_GUIDE.md
  - docs/milestones/m14/MOBILE_DEPLOYMENT_GUIDE.md
  - docs/milestones/m14/CLIENT_ACCEPTANCE_CHECKLIST.md
---

# Client Deployment Report (M14E)

## Executive Summary

Milestone **14E** prepares **production client deployment** for WEBSTUDIO IMS across Windows desktop, macOS desktop, Android, and iOS. Validation extends existing client connectivity, discovery, auth, and mobile offline/barcode stacks with a commissioning API and operator documentation — **no new business features or UI redesign**.

| Deliverable | Path |
|-------------|------|
| Desktop Deployment Guide | [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md) |
| Mobile Deployment Guide | [MOBILE_DEPLOYMENT_GUIDE.md](MOBILE_DEPLOYMENT_GUIDE.md) |
| Client Acceptance Checklist | [CLIENT_ACCEPTANCE_CHECKLIST.md](CLIENT_ACCEPTANCE_CHECKLIST.md) |

**Verdict:** Client deployment preparation is **implemented and test-covered**.

---

## Validation matrix

### Desktop

| Requirement | Check key | Implementation |
|-------------|-----------|----------------|
| Install EXE | `desktop_install_exe` | NSIS `WEBSTUDIO Desktop Setup.exe` |
| Install DMG | `desktop_install_dmg` | electron-builder DMG universal |
| Connect automatically | `desktop_connect_automatically` | `ConnectionReconnectService.ts` |
| Discover server | `desktop_discover_server` | mDNS + `SavedServerStore` |
| Authenticate | `desktop_authenticate` | JWT login + setup gate |
| Verify permissions | `desktop_verify_permissions` | `permissionArchitecture.ts` |

### Flutter (Android)

| Requirement | Check key | Implementation |
|-------------|-----------|----------------|
| Install APK | `flutter_install_apk` | `release/mobile/WEBSTUDIO IMS.apk` |
| Connect | `flutter_connect` | Server preferences + discovery |
| Restore session | `flutter_restore_session` | `AuthRepository.restoreSession` |
| Offline validation | `flutter_offline_validation` | `core/offline/*` stack |
| Camera validation | `flutter_camera_validation` | On-device acceptance (procedural) |
| Barcode validation | `flutter_barcode_validation` | `barcode_scanner_screen.dart` |

### iOS

| Requirement | Check key | Implementation |
|-------------|-----------|----------------|
| Installation architecture | `ios_installation_architecture` | arm64, bundle ID, Xcode Archive |
| Validate installation | `ios_validate_installation` | TestFlight / Ad Hoc + local network |
| macOS update channel | `desktop_macos_update_channel` | DMG desktop (paired artifact) |

---

## API surface

```http
GET /api/v1/deployment/client-validation
```

Requires network administrator permission. Returns platform checks, artifact paths, acceptance checklist items, and version gates.

Public endpoints used by clients:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/discovery/health` | Server discovery |
| `GET /api/v1/version` | Compatibility |
| `GET /api/v1/setup/status` | Setup gate |
| `POST /api/v1/auth/login` | Authentication |
| `GET /api/v1/auth/me` | Permissions |
| `GET /api/v1/client-updates/check` | Platform updates |

---

## Code references

| Component | Path |
|-----------|------|
| Production validation | `services/client_deployment_validation_service.py` |
| API router | `api/routers/client_deployment.py` |
| Desktop reconnect | `apps/desktop/src/services/ConnectionReconnectService.ts` |
| Desktop discovery | `apps/desktop/electron/mdns-discovery.ts` |
| Mobile session | `apps/mobile_flutter/lib/features/auth/data/auth_repository.dart` |
| Mobile offline | `apps/mobile_flutter/lib/core/offline/` |
| Mobile barcode | `apps/mobile_flutter/lib/features/inventory/presentation/barcode_scanner_screen.dart` |
| Installer guide | `docs/milestones/m12c/INSTALLER_GUIDE.md` |
| Unit tests | `tests/deployment/test_client_deployment_validation.py` |

---

## Commissioning sequence

1. Complete server install (M14A) and networking (M14B).
2. Build or obtain release artifacts from M12C / Deployment Center.
3. `GET /deployment/client-validation` on server.
4. Deploy desktop to admin PC first ([DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md)).
5. Sideload Android APK; pilot iOS ([MOBILE_DEPLOYMENT_GUIDE.md](MOBILE_DEPLOYMENT_GUIDE.md)).
6. Complete [CLIENT_ACCEPTANCE_CHECKLIST.md](CLIENT_ACCEPTANCE_CHECKLIST.md).
7. Roll out remaining staff devices.

---

## Test evidence

```
pytest apps/backend/tests/deployment/test_client_deployment_validation.py — 2 passed
```

---

## Sign-off

| Criterion | Status |
|-----------|--------|
| Desktop deployment guide | ✅ |
| Mobile deployment guide | ✅ |
| Client acceptance checklist | ✅ |
| Production validation API | ✅ |
| Unit tests passing | ✅ |

**M14E complete. STOP.**
