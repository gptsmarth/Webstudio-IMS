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
- **No File/Edit/View menu bar** in production builds (native app chrome only)

### Windows code signing (Smart App Control / SmartScreen)

Unsigned builds are blocked or warned on Windows 11 **Smart App Control**. Production releases should be **Authenticode-signed**.

1. Purchase a **Windows code signing certificate** (OV or EV from a trusted CA). EV certs gain reputation faster.
2. Export the certificate as a `.pfx` file.
3. Base64-encode the PFX for GitHub Actions:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\webstudio-codesign.pfx")) | Set-Clipboard
   ```
4. Add repository secrets:
   | Secret | Value |
   |--------|--------|
   | `WIN_CSC_LINK` | Base64-encoded `.pfx` |
   | `WIN_CSC_KEY_PASSWORD` | PFX password |

CI (`.github/workflows/release.yml`) passes these to `electron-builder`, which signs `WEBSTUDIO Desktop Setup.exe` automatically when secrets are present. Builds without secrets still compile but remain unsigned.

Local signed build:

```powershell
$env:CSC_LINK = "C:\path\webstudio-codesign.pfx"
$env:CSC_KEY_PASSWORD = "your-password"
pnpm desktop:package:win
```


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

**CI / release build** (`build-server-setup.ps1`) automatically stages:

- **Embedded Python 3.12** + backend dependencies → `{InstallRoot}\runtime\python\`
- **NSSM** → `{InstallRoot}\tools\nssm\nssm.exe`

No manual venv or NSSM copy is required on the target server.

### Build

```powershell
# Install Inno Setup 6, then:
powershell -ExecutionPolicy Bypass -File scripts/release/build-server-setup.ps1
```

`build-server-setup.ps1` runs `stage-server-payload.ps1` first (downloads Python embed + NSSM, `pip install -e apps/backend`), then compiles the installer.

**Output:** `release/server/WEBSTUDIO Server Setup.exe`

### Installer actions

1. **Detect PostgreSQL** — any Windows service `postgresql-x64-*` (16, 17, 18, …)
2. **Install PostgreSQL** — silent install from optional payload if bundled and missing
3. **Copy bundled runtime** — Python + NSSM (no separate Python install on server)
4. **Create directories** — `logs`, `backups`, `certs`, `exports`
5. **Generate production `.env`** — from template + random JWT secret (`API_PORT=8000`)
6. **Run Alembic** — `alembic upgrade head` (requires existing `webstudio` database)
7. **Configure WEBSTUDIO Server Service** — NSSM, Automatic Delayed Start
8. **Configure recovery** — restart on failure

Post-install runs **visibly**; failures are logged to `logs\install-post.log`.

**Administrator prerequisite:** PostgreSQL installed with `webstudio` database and `webstudio_app` user before or after setup (migrations need a reachable database).

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
