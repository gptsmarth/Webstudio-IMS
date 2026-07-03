---
Title: Installer Guide — Production Release
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12C
---

# Installer Guide — WEBSTUDIO IMS Production Release

Guide for building and distributing M12C release artifacts. **No UI changes** — packaging and branding only.

---

## Prerequisites

| Tool | Version | Used for |
|------|---------|----------|
| Node.js | ≥20 | Desktop packaging |
| pnpm | ≥9 | Monorepo |
| Flutter | stable 3.x | Mobile APK / iOS |
| Inno Setup | 6.x | Server Setup.exe |
| NSSM | latest | Server Windows service (installed by server setup) |
| Python | 3.12+ | Server runtime |

---

## 1. Windows Desktop — `WEBSTUDIO Desktop Setup.exe`

### Build

```powershell
pnpm install
pnpm desktop:package:win
```

**Output:** `apps/desktop/release/desktop/WEBSTUDIO Desktop Setup.exe`

### Installer behaviour

- Per-machine NSIS install  
- Start Menu + Desktop shortcuts  
- Branded with `icon.ico` (WEBSTUDIO)  
- Uninstaller included  

### Install (end user)

1. Run `WEBSTUDIO Desktop Setup.exe`  
2. Launch **WEBSTUDIO Desktop** from Start Menu  
3. Connect to server URL (saved locally; auto-reconnect after server reboot)  

---

## 2. macOS Desktop — `WEBSTUDIO Desktop.dmg`

### Build

```bash
pnpm install
pnpm desktop:package:mac
```

**Output:** `apps/desktop/release/desktop/WEBSTUDIO Desktop.dmg`

### Notes

- Universal build targets x64 + arm64  
- Code signing/notarization: set `CSC_LINK` / `APPLE_*` env vars before build when certificates are available  
- Drag-to-Applications DMG layout  

---

## 3. Android — `WEBSTUDIO IMS.apk`

### Signing setup (one time)

```bash
keytool -genkey -v -keystore apps/mobile_flutter/android/keystores/webstudio-release.keystore \
  -alias webstudio -keyalg RSA -keysize 2048 -validity 10000

cp apps/mobile_flutter/android/key.properties.example apps/mobile_flutter/android/key.properties
# Edit key.properties with keystore paths and passwords
```

### Build

```bash
pnpm release:sync-branding
pnpm release:android
```

**Output:** `release/mobile/WEBSTUDIO IMS.apk`

### Branding

- Launcher icons regenerated from `apps/desktop/public/assets/webstudio/icon.png`  
- White splash via `flutter_native_splash`  
- **No AAB** — APK only per M12 scope  

---

## 4. iOS — Release / IPA

### Configure signing

1. Open `apps/mobile_flutter/ios/Runner.xcworkspace` in Xcode  
2. Set **Team** on Runner target (Signing & Capabilities)  
3. Or set `DEVELOPMENT_TEAM` in `ios/Flutter/Release.xcconfig`  

Bundle ID: `com.webstudio.webstudio_ims` (aligned with Android)

### Build

```bash
pnpm release:sync-branding
bash scripts/release/build-ios-ipa.sh
```

### Archive / IPA (Xcode)

1. Product → Archive (Release configuration)  
2. Distribute App → Custom → `ios/ExportOptions.plist`  
3. Output IPA for enterprise / ad-hoc distribution  

**No App Store Connect assets** in this milestone.

---

## 5. Windows Server — `WEBSTUDIO Server Setup.exe`

### Payload preparation

Optional: place PostgreSQL 16 installer at:

`infra/windows/server-installer/payload/postgresql-installer.exe`

Server release tree must include:

- `apps/backend` (Python package)  
- `database/` (migrations)  
- Python venv at `{InstallRoot}\venv` (create before or extend installer)  
- NSSM at `{InstallRoot}\tools\nssm\nssm.exe`  

### Build

```powershell
# Install Inno Setup 6, then:
powershell -ExecutionPolicy Bypass -File scripts/release/build-server-setup.ps1
```

**Output:** `release/server/WEBSTUDIO Server Setup.exe`

### Installer actions

1. **Detect PostgreSQL** — Windows service `postgresql-x64-16`  
2. **Install PostgreSQL** — silent install from payload if bundled and missing  
3. **Create directories** — `logs`, `backups`, `certs`, `exports`  
4. **Generate production `.env`** — from template + random JWT secret  
5. **Run Alembic** — `alembic upgrade head`  
6. **Configure WEBSTUDIO Server Service** — NSSM, Automatic Delayed Start  
7. **Configure recovery** — restart on failure  

See [M12B Windows Service Guide](../m12b/WINDOWS_SERVICE_GUIDE.md).

---

## Version bump

```bash
bash scripts/release/bump-version.sh 0.1.0 1
git tag v0.1.0
git push origin v0.1.0
```

CI workflow `.github/workflows/release.yml` builds artifacts on tag push.

---

## Verification checklist

- [ ] No Electron or Flutter default icons visible  
- [ ] Splash / launcher: WEBSTUDIO dark logo on white  
- [ ] Desktop Setup installs and launches  
- [ ] Server Setup creates service and `/health/ready` returns OK  
- [ ] APK installs over Wi‑Fi sideload  
- [ ] iOS Archive succeeds with team cert  
- [ ] Clients reconnect after server power cycle  

---

## Related

- [PACKAGING_CONFIGURATION.md](./PACKAGING_CONFIGURATION.md)  
- [M12 Global Rules](../m12/M12_GLOBAL_RULES.md)  
- [Branding Matrix](../m12/BRANDING_PACKAGING_MATRIX.md)
