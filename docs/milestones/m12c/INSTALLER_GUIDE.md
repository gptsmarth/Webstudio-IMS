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
# After changing icon.png or icon design:
bash scripts/release/regenerate-branding-icons.sh
pnpm desktop:package:win
```

`desktop:package:win` validates `icon.ico` / `icon.png` before packaging. In-app logos (`logo.svg`, `brand-logos/*`) ship automatically from `apps/desktop/public/assets/` via Vite (`base: './'`).

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

### Sign and notarize for office Macs

An Apple Developer Program Account Holder can create a **Developer ID Application**
certificate in **Xcode → Settings → Accounts → team → Manage Certificates**.
Use **Keychain Access → My Certificates** to export the certificate and private
key together as a password-protected `.p12` file. Store the file outside the
repository. [Apple certificate setup](https://developer.apple.com/help/account/certificates/create-developer-id-certificates)

Create an app-specific password in **Apple Account → Sign-In and Security →
App-Specific Passwords**. Use the Apple Account authorized for notarization and the
Team ID shown under **Apple Developer → Membership details**.
[Apple app-specific passwords](https://support.apple.com/en-us/102654)

For a GitHub build, enter these values under **Settings → Secrets and variables →
Actions → New repository secret** in the authorized release repository.

| Secret | Value |
|--------|-------|
| `MAC_CSC_LINK` | Base64 of the exported `.p12` |
| `MAC_CSC_KEY_PASSWORD` | Password set during the export |
| `APPLE_ID` | Apple Account email authorized for notarization |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password |
| `APPLE_TEAM_ID` | Apple Developer Team ID |

With GitHub CLI authenticated to the authorized repository, you can send the
Base64 certificate directly to the secret without printing it.

```bash
base64 -i "/path/to/WEBSTUDIO-signing.p12" | gh secret set MAC_CSC_LINK --repo OWNER/REPO
```

### Build

```bash
pnpm install
pnpm desktop:package:mac
```

For a local signed build, provide the `.p12` path as `CSC_LINK`, its password
as `CSC_KEY_PASSWORD`, and the three `APPLE_*` values in the build environment.
With signing credentials, the script checks the Intel and Apple silicon slices,
the app signature, the attached notarization ticket, and Gatekeeper acceptance.
It produces `apps/desktop/release/desktop/WEBSTUDIO Desktop.dmg`. The
`WEBSTUDIO Desktop-dev.dmg` output is for build validation.

Open the signed DMG, drag **WEBSTUDIO Desktop** into **Applications**, and launch
it with Gatekeeper enabled. From Terminal, you can also confirm the installed copy
with `spctl --assess --type execute -vv "/Applications/WEBSTUDIO Desktop.app"`.
[Apple notarization guide](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution)

---

## 3. Android — `WEBSTUDIO IMS.apk`

Use Flutter **3.44.4**, which supports the repository's Gradle **9.1.0**
and Android Gradle Plugin **9.0.1**. The Android release job uses **JDK 17**.
The shared CI setup pins Flutter for checks and mobile packaging. Release scripts use the committed
`apps/mobile_flutter/pubspec.lock`. Update the toolchain and lockfile together
when upgrading Flutter.

The Android build adds AndroidX Concurrent Futures to the CameraX plugin's
compile classpath. CameraX already supplies it at runtime.

The APK script validates the committed lockfile before building. The release
build runs Flutter's normal plugin registration so development-only plugins such
as `integration_test` stay out of the APK.

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

### Set up TestFlight on a Mac

1. Install full Xcode 26 or later with the iOS SDK, Flutter 3.44.4, and CocoaPods.
   Open Xcode once to finish setup. In **Xcode → Settings → Locations**, select
   that Xcode version under **Command Line Tools**. Confirm with
   `xcodebuild -version`, then add your Apple Developer team account in
   **Xcode → Settings → Accounts**.
   [Apple upload requirements](https://developer.apple.com/news/upcoming-requirements/)
2. Register or reuse the explicit iOS App ID `com.webstudio.webstudioIms` on that
   team. In **App Store Connect → Apps**, create or open the iOS app record using
   the same ID. [App record setup](https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app/)
3. Prepare the corrected checkout from the repository root.

   ```bash
   bash scripts/release/sync-branding-assets.sh
   cd apps/mobile_flutter
   flutter config --no-enable-swift-package-manager
   flutter pub get --enforce-lockfile
   dart run flutter_launcher_icons
   dart run flutter_native_splash:create
   flutter build ios --config-only --release --no-codesign --no-pub
   open ios/Runner.xcworkspace
   ```

4. In Xcode, select the **Runner** target, then **Signing & Capabilities**. Enable
   **Automatically manage signing** and select the Apple Developer team. Keep
   team-specific settings local. Choose the **Runner** scheme and a generic iOS
   device destination, then **Product → Archive**.
5. In **Organizer → Archives**, select the archive and choose **Distribute App →
   App Store Connect → Upload**. Use a unique build number for each upload. If
   needed, add `--build-number=<number>` to the Flutter configuration command
   before archiving.
   [Apple upload instructions](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds/)
6. After processing in **App Store Connect → TestFlight**, add the build to a
   tester group and invite users by email. Use internal testing for authorized
   App Store Connect users. The first build used for external testing goes
   through TestFlight App Review. On the iPhone, install **TestFlight** from the
   App Store and accept the invitation. TestFlight builds expire after 90 days.
   [Apple TestFlight overview](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)

For ongoing private staff distribution, use a **Custom App** assigned to your
organization through Apple Business.
[Apple private distribution](https://developer.apple.com/custom-apps/)

### Export a signed IPA for registered devices

```bash
WEBSTUDIO_IOS_EXPORT_OPTIONS_PLIST=/absolute/path/to/ExportOptions.plist \
  bash scripts/release/build-ios-ipa.sh
```

Use a provisioned Mac with the intended Apple Developer team. The
`apps/mobile_flutter/ios/ExportOptions.plist` in the repository is for
registered-device export. The signed output is `release/mobile/WEBSTUDIO IMS.ipa`.

GitHub Actions keeps an unsigned `.xcarchive` for compile validation. For device
acceptance, join the office Wi-Fi, grant **Local Network** permission, and connect
to the office server's trusted HTTPS address. Verify login, inventory search,
barcode scanning with **Camera** permission, and reopening the app on a physical
iPhone.

---

## 5. Windows Server — `WEBSTUDIO Server Setup.exe`

### Payload preparation

**CI / release build** (`build-server-setup.ps1`) automatically stages:

- **Embedded Python 3.12** + backend dependencies → `{InstallRoot}\runtime\python\`
- **NSSM** → `{InstallRoot}\tools\nssm\nssm.exe`

No manual venv or NSSM copy is required on the target server.

### Build

```powershell
# Install Inno Setup 6, then:
powershell -ExecutionPolicy Bypass -File scripts/release/build-server-setup.ps1
```

`build-server-setup.ps1` runs `stage-server-payload.ps1` first (downloads Python embed + NSSM, `pip install apps/backend`), then compiles the installer.

**Output:** `release/server/WEBSTUDIO Server Setup.exe`

### Installer actions

1. **Fresh setup** — leave the manual database task unchecked. If no PostgreSQL
   service is found, Setup downloads the pinned PostgreSQL 18 Windows installer
   from EDB over HTTPS, checks its SHA-256, and prompts for the PostgreSQL
   administrator password. It installs the engine and database tools, then
   limits the new instance to loopback. Internet access is required for this download.
2. **Database setup** — supply the `webstudio_app` password when prompted. If a
   PostgreSQL service is already installed, Setup asks which instance and port
   to use when needed. It reuses a working `webstudio` login, or asks for the
   existing PostgreSQL administrator password to create missing database objects.
   Password entry is masked. The service uses the application password from
   the restricted `.env`, while the administrator password is used during setup.
3. **Manual setup** — provision PostgreSQL 16 or newer, `webstudio`, and
   `webstudio_app` first. Select **Use a PostgreSQL database I set up myself
   (skip automatic provisioning)** in Setup. You can also configure
   `DATABASE_URL` beforehand for an existing/custom PostgreSQL installation.
4. **Upgrade** — run Setup into the existing server's installation folder. It
   skips the database choice when the server service or a configured `.env`
   already exists. It uses the saved database connection and existing Windows
   service, then applies pending Alembic migrations. If the connection fails,
   correct it and rerun Setup with the same database. Deployment Center can download packages for
   Windows production. Apply the verified server installer on the server during
   a maintenance window after verifying a full backup and saving the live
   `.env` privately.
5. **Start and verify** — Setup starts the IMS service and checks the HTTP
   readiness endpoint. If you already use TLS, verify `/health/ready` at the
   certified HTTPS URL. Installation problems are reported in `logs\install-post.log`.
   Restore the chosen backup from the Desktop Restore Center after Setup is ready.
6. **Office LAN access** — after local setup or recovery is complete, run the
   bundled `infra\windows\configure-firewall.ps1 -Enable` in Administrator
   Windows PowerShell. Setup prints the installed command in
   `logs\install-post.log`. It selects a single eligible Private IPv4
   connection and uses the configured API port, with TCP 8000 as the default.
   Use `-ServerIp`, `-Subnet`, and `-ApiPort` to specify the firewall
   scope. Rerun it when that scope changes. Use `-Disable` to close the
   managed API rule. Keep the staff connection Private and leave PostgreSQL
   on loopback. [Office firewall configuration](../m14/FIREWALL_CONFIGURATION_GUIDE.md#2-automated-configuration)

Enterprise Release and Server Release both compile this installer from the
selected Git commit using `scripts/release/build-server-setup.ps1`.

See [M12B Windows Service Guide](../m12b/WINDOWS_SERVICE_GUIDE.md).

If an upgrade already copied the files and then failed while configuring
`AppEnvironmentExtra`, rerun the corrected installer in the same folder. To
recover before a corrected installer is available, replace the installed
`infra\windows\webstudio-env.ps1` with the corrected script and resume post-install
in Administrator Windows PowerShell.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'D:\WEBSTUDIO-IMS\infra\windows\server-installer\invoke-server-post-install.ps1' -InstallRoot 'D:\WEBSTUDIO-IMS'
```

Check `logs\install-post.log` for `Post-install completed successfully.` and
verify `/health/ready` at the server's configured API URL.

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
