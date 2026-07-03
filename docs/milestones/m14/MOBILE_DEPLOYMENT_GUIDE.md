---
Title: Mobile Deployment Guide — Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14E
Related Documents:
  - docs/milestones/m14/CLIENT_ACCEPTANCE_CHECKLIST.md
  - docs/milestones/m12c/INSTALLER_GUIDE.md
  - docs/milestones/m12h/IOS_GUIDE.md
  - docs/milestones/m12h/ANDROID_GUIDE.md
---

# Mobile Deployment Guide (M14E)

Production guide for **Flutter** clients: **Android APK** and **iOS**.

**Prerequisites:** Server on store LAN; staff devices on same Wi‑Fi/VLAN (M14B).

---

## 1. Artifacts

| Platform | Artifact | Build |
|----------|----------|-------|
| **Android** | `WEBSTUDIO IMS.apk` | `pnpm release:android` |
| **iOS** | IPA (Ad Hoc / TestFlight / Enterprise) | `bash scripts/release/build-ios-ipa.sh` |

Paths: `release/mobile/`  
Bundle ID: `com.webstudio.webstudio_ims`

Updates: server-only via `/api/v1/client-updates/check` — **never GitHub**.

---

## 2. Android — install APK

### IT preparation

1. Configure `android/key.properties` and release keystore (one-time).
2. Build signed APK: `pnpm release:sync-branding && pnpm release:android`.
3. Copy APK to device or internal download page on server.

### Staff installation

1. Enable **Install unknown apps** for file manager / browser (Android 8+).
2. Open APK → Install.
3. Launch **WEBSTUDIO IMS**.

**Pass:** App icon and splash show WEBSTUDIO branding.

---

## 3. Connect (Android & iOS)

1. Join **store Wi‑Fi** (same subnet as server).
2. Open app → allow **Local Network** when prompted (iOS 14+).
3. Server discovered automatically or enter `http://<server-ip>:8000`.
4. **Test connection** → Save.
5. Log in with staff credentials.

Saved servers: `SavedServer` list with hostname metadata for roaming.

---

## 4. Restore session

On app restart:

1. `AuthRepository.restoreSession()` runs at startup.
2. If refresh token valid → silent token refresh.
3. If offline but cached profile exists → limited offline mode.
4. If expired → login screen with session-expired message.

**Validation:** Kill app → reopen → still logged in (on LAN).  
**Validation:** Airplane mode → cached profile may allow read-only offline.

---

## 5. Offline validation

| Feature | Behaviour |
|---------|-----------|
| Offline banner | Shows when API unreachable |
| Cached inventory | Last synced workspace data |
| Pending operations | Queue transfers/sales when back online |
| Dashboard cache | Stale indicator when offline |

**Drill:**

1. Load inventory on Wi‑Fi.
2. Enable airplane mode.
3. Confirm offline banner and cached serial lookup.
4. Disable airplane mode → pending sync completes.

Implementation: `apps/mobile_flutter/lib/core/offline/`

---

## 6. Camera validation

**Requires physical device** (not emulator-only sign-off).

1. Open inventory → serial field → **Scan barcode**.
2. Grant **Camera** permission when prompted.
3. Point at test serial barcode (Code 128 / QR per label).
4. Serial populates lookup field.

Files: `barcode_scan_launcher.dart`, `barcode_scanner_screen.dart`

**Pass:** Scan returns correct serial; torch toggle works.

---

## 7. Barcode validation

| Mode | Platform |
|------|----------|
| Camera scan | Android / iOS |
| Keyboard wedge | Desktop (USB scanner) |

Mobile flow:

1. Scan → `lookupBySerial` (online or cached offline).
2. Item detail sheet opens if found.

**Pass:** Known serial resolves; unknown serial shows appropriate message.

---

## 8. iOS — installation architecture

| Item | Value |
|------|-------|
| Minimum iOS | 14.0 |
| Architecture | arm64 (device); simulator excluded from production |
| Signing | Apple Development / Distribution certificate |
| Capabilities | Local Network, Camera |
| Distribution | TestFlight (recommended), Ad Hoc, Enterprise MDM |

### Build validation (IT)

```bash
bash scripts/release/build-ios-ipa.sh
```

Xcode: Product → Archive → Validate App → Distribute.

**Pass:** Archive succeeds; IPA installs on registered test device.

### First launch (iOS)

1. Settings → Privacy → Local Network → allow WEBSTUDIO IMS.
2. Discover server or manual URL.
3. Login.

See [IOS_GUIDE.md](../m12h/IOS_GUIDE.md).

---

## 9. macOS desktop note

**DMG** is the **macOS desktop** installer (not iOS). See [DESKTOP_DEPLOYMENT_GUIDE.md](DESKTOP_DEPLOYMENT_GUIDE.md) for Mac staff PCs.

---

## 10. Production validation

```http
GET /api/v1/deployment/client-validation
```

Review `flutter_*` and `ios_*` checks.

---

## 11. Troubleshooting

| Symptom | Fix |
|---------|-----|
| APK blocked | Enable unknown sources |
| iOS local network | Privacy settings |
| Session lost | Re-login; check token policy |
| Camera black | Permission; physical device |
| Offline empty cache | Sync once on Wi‑Fi first |

---

## 12. Sign-off

Complete mobile sections of [CLIENT_ACCEPTANCE_CHECKLIST.md](CLIENT_ACCEPTANCE_CHECKLIST.md) (CLI-06–CLI-11).
