---
Title: M12 Branding & Packaging Matrix
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: M12
Related Documents: docs/milestones/m12/M12_GLOBAL_RULES.md
---

# M12 Branding & Packaging Matrix

Maps each **M12 branding requirement** to the canonical asset, consuming code/config, and current status.

**Brand rule:** WEBSTUDIO **dark logo** on **white** for installer/splash/launcher surfaces.

---

## Canonical asset registry

| Path | Purpose |
|------|---------|
| `apps/desktop/public/assets/webstudio/logo-dark.svg` | Dark logo (light backgrounds) |
| `apps/desktop/public/assets/webstudio/logo-light.svg` | Light logo (dark UI — in-app only) |
| `apps/desktop/public/assets/webstudio/icon.ico` | Windows icon |
| `apps/desktop/public/assets/webstudio/icon.icns` | macOS icon |
| `apps/desktop/public/assets/webstudio/icon.png` | 1024×1024 fallback |
| `apps/desktop/public/assets/webstudio/splash.svg` | Splash artwork |
| `apps/desktop/public/assets/webstudio/favicon.svg` | Dev/web favicon |

Desktop runtime registry: `apps/desktop/src/registries/AssetManifest.ts`, `WebstudioAssetRegistry.ts`.

---

## Requirement matrix

| Requirement | Canonical asset | Consumer | Status | M12 action |
|-------------|-----------------|----------|--------|------------|
| Windows EXE installer | `icon.ico` + NSIS banner | `electron-builder` (to add) | ⏳ Not configured | Add `electron-builder` + NSIS branding |
| macOS DMG | `icon.icns` + DMG background | `electron-builder` (to add) | ⏳ Not configured | Add DMG target + volume icon |
| Desktop app icon | `icon.ico` / `icon.icns` | Electron `BrowserWindow` / bundle | ⚠️ Partial | Wire `electron-builder` `icon` fields |
| Taskbar icon | Same as app icon | Electron main process | ⚠️ Partial | Verify packaged `.exe` embeds ICO |
| Start Menu icon | Installer + shortcut | NSIS | ⏳ | Installer shortcut icon from ICO |
| Splash screen | `splash.svg` + white bg | `SplashScreen.tsx` | ✅ Uses registry | Ensure splash uses **logo-dark on white** only (no layout change) |
| About screen | `logo-dark.svg` | Settings / About panel | ✅ Registry exists | Asset swap only if needed |
| Android launcher | Derived from `icon.png` | `mipmap-*/ic_launcher.png` | ⚠️ Flutter defaults | Regenerate from registry via `flutter_launcher_icons` |
| Android splash | White + logo-dark | `launch_background.xml` / native splash | ⏳ | Add `flutter_native_splash` config |
| iOS app icon | Derived from `icon.png` | `AppIcon.appiconset` | ⚠️ Flutter defaults | Regenerate icon set from registry |
| iOS launch screen | White + logo-dark | `LaunchScreen.storyboard` / assets | ⏳ | Native splash generation |
| Installer graphics | Logo-dark on white PNG/SVG | NSIS / DMG | ⏳ | Export installer banners from registry |
| Uninstaller | Same as installer | NSIS | ⏳ | Branded uninstaller with `electron-builder` |
| Version information | Product name + semver | `package.json`, Electron, Gradle, Xcode | ⚠️ 0.1.0 scattered | Unified version bump script (M12 C3) |

---

## Release artifact matrix

| Artifact | Build command (target) | Status |
|----------|------------------------|--------|
| `WEBSTUDIO Desktop Setup.exe` | `pnpm --filter @webstudio/desktop package:win` | ⏳ Script not yet added |
| `WEBSTUDIO Desktop.dmg` | `pnpm --filter @webstudio/desktop package:mac` | ⏳ Script not yet added |
| `WEBSTUDIO IMS.apk` | `flutter build apk --release` | ⏳ Signing config pending |
| iOS Release / IPA | Xcode Archive / `flutter build ipa` | ⏳ Provisioning pending |

---

## Flutter asset sync strategy (extend-only)

1. **Single source:** `apps/desktop/public/assets/webstudio/icon.png` (1024×1024, dark mark on transparent or white).
2. **Generate platform icons** with dev dependency tooling — no hand-editing every mipmap.
3. **Do not** change Flutter widget trees — only replace `assets/` and native resource folders.

Suggested tools (M12 implementation):

- `flutter_launcher_icons` — Android/iOS/macOS/Windows launcher icons
- `flutter_native_splash` — Android/iOS splash (white background + centered logo-dark)

---

## Desktop packaging strategy (extend-only)

Add to `apps/desktop/package.json` (no UI code changes):

```json
"package:win": "electron-builder --win nsis",
"package:mac": "electron-builder --mac dmg"
```

Configuration file: `apps/desktop/electron-builder.yml` pointing at `public/assets/webstudio/icon.*`.

Product names:

- `productName`: `WEBSTUDIO Desktop`
- APK name: `WEBSTUDIO IMS.apk` (via Gradle `archivesBaseName` or output rename script)

---

## Out of scope (per M12 rules)

- Play Store / App Store listing graphics
- UI layout changes on Desktop or Flutter
- Rewriting Tally, backup, RBAC, or backend modules
- New features beyond production gates (demo mode off, CSP, etc. tracked separately in 11Y checklist)

---

## Verification before customer release

1. Install each artifact on a clean machine / device.
2. Confirm **no** Flutter or Electron default icons visible.
3. Confirm About / splash / launcher show **WEBSTUDIO dark logo on white**.
4. Run smoke: login, inventory read, Tally status, backup list.
5. Sign off checklist sections D, E, F in [RELEASE_CHECKLIST.md](../m11y/RELEASE_CHECKLIST.md).
