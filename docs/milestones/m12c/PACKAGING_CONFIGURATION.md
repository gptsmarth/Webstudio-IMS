---
Title: Packaging Configuration Reference
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12C
---

# Packaging Configuration Reference — M12C

File map for production release configuration. **Stop point:** configuration complete; run build scripts on build machines to produce artifacts.

---

## Desktop (Electron)

| File | Purpose |
|------|---------|
| `apps/desktop/electron-builder.yml` | NSIS + DMG targets, artifact names, icons |
| `apps/desktop/build/entitlements.mac.plist` | macOS hardened runtime entitlements |
| `apps/desktop/package.json` | `electron-builder` dep; `package:win` / `package:mac` scripts |
| `apps/desktop/electron/main.ts` | Window icon from branding registry; build version injection |
| `apps/desktop/public/assets/webstudio/*` | Canonical ICO, ICNS, PNG, splash |

**Artifact names (configured):**

- Windows: `WEBSTUDIO Desktop Setup.exe`  
- macOS: `WEBSTUDIO Desktop.dmg`  

---

## Mobile (Flutter)

| File | Purpose |
|------|---------|
| `apps/mobile_flutter/pubspec.yaml` | `flutter_launcher_icons`, `flutter_native_splash` |
| `apps/mobile_flutter/android/app/build.gradle.kts` | Release signing, APK filename |
| `apps/mobile_flutter/android/key.properties.example` | Keystore template |
| `apps/mobile_flutter/android/app/src/main/AndroidManifest.xml` | `@string/app_name` → WEBSTUDIO IMS |
| `apps/mobile_flutter/ios/ExportOptions.plist` | IPA export (release-testing) |
| `apps/mobile_flutter/ios/Flutter/Release.xcconfig` | Release signing placeholders |
| `apps/mobile_flutter/ios/Runner/Info.plist` | Display name WEBSTUDIO IMS |
| `apps/mobile_flutter/ios/Runner.xcodeproj/project.pbxproj` | Bundle ID `com.webstudio.webstudio_ims` |

**Artifact name:** `WEBSTUDIO IMS.apk` (also Gradle output `WEBSTUDIO-IMS-{version}.apk`)

**Explicitly not configured:** AAB, Play Store assets, App Store listing.

---

## Server (Windows)

| File | Purpose |
|------|---------|
| `infra/windows/server-installer/WEBSTUDIO-Server-Setup.iss` | Inno Setup master script |
| `infra/windows/server-installer/server-install-post.ps1` | Folders, .env, pip, Alembic, NSSM |
| `infra/windows/server-installer/payload/` | Optional PostgreSQL installer |
| `infra/windows/install-webstudio-service.ps1` | Windows service registration |
| `infra/windows/configure-service-recovery.ps1` | Failure recovery |
| `config/env/.env.production.template` | Production config template |

**Artifact name:** `WEBSTUDIO Server Setup.exe`

---

## Release scripts

| Script | Output |
|--------|--------|
| `scripts/release/bump-version.sh` | Sync semver across manifests |
| `scripts/release/sync-branding-assets.sh` | Desktop registry → Flutter assets |
| `scripts/release/build-desktop-win.ps1` | Setup.exe |
| `scripts/release/build-desktop-mac.sh` | DMG |
| `scripts/release/build-android-apk.sh` | APK |
| `scripts/release/build-ios-ipa.sh` | Xcode archive / IPA |
| `scripts/release/build-server-setup.ps1` | Server Setup.exe |

---

## CI

`.github/workflows/release.yml` — tag `v*.*.*` triggers artifact builds (iOS job disabled until signing secrets).

---

## Branding replacement summary

| Surface | Source | Mechanism |
|---------|--------|-----------|
| Windows desktop icon | `icon.ico` | electron-builder + BrowserWindow |
| macOS desktop icon | `icon.icns` | electron-builder + BrowserWindow |
| NSIS installer | `icon.ico` | electron-builder nsis.* |
| Android launcher | `icon.png` | flutter_launcher_icons |
| Android splash | white + icon | flutter_native_splash |
| iOS App Icon | `icon.png` | flutter_launcher_icons |
| iOS launch | white + icon | flutter_native_splash |
| Server installer | `icon.ico` | Inno Setup SetupIconFile |

Run before first mobile release build:

```bash
pnpm release:sync-branding
cd apps/mobile_flutter && dart run flutter_launcher_icons && dart run flutter_native_splash:create
```

---

## Next steps (post-configuration)

1. Install `electron-builder` deps: `pnpm install` in monorepo root  
2. Configure Android `key.properties` for release signing  
3. Configure Apple `DEVELOPMENT_TEAM` for iOS  
4. Bundle PostgreSQL installer in server payload (optional)  
5. Run build scripts on target OS machines  
6. Execute verification checklist in [INSTALLER_GUIDE.md](./INSTALLER_GUIDE.md)
