---
Title: Milestone 12C — Production Packaging Index
Version: 1.0.0
Status: Complete — Configuration Ready
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12C
---

# Milestone 12C — Production Packaging

Packaging **configuration** for all M12 release artifacts. UI unchanged — branding and build config only.

## Target artifacts

| Platform | Artifact | Build command |
|----------|----------|---------------|
| Windows Desktop | `WEBSTUDIO Desktop Setup.exe` | `pnpm desktop:package:win` |
| macOS Desktop | `WEBSTUDIO Desktop.dmg` | `pnpm desktop:package:mac` |
| Android | `WEBSTUDIO IMS.apk` | `pnpm release:android` |
| iOS | Release IPA / Archive | `bash scripts/release/build-ios-ipa.sh` |
| Windows Server | `WEBSTUDIO Server Setup.exe` | `scripts/release/build-server-setup.ps1` |

## Documentation

- [INSTALLER_GUIDE.md](./INSTALLER_GUIDE.md) — operator and build engineer guide
- [PACKAGING_CONFIGURATION.md](./PACKAGING_CONFIGURATION.md) — file map and settings reference

## Branding source

`apps/desktop/public/assets/webstudio/` — all platform icons and installer graphics.

## Out of scope (M12 rules)

- Play Store / App Store listing assets  
- Android App Bundle (AAB)  
- App Store Connect submission  
