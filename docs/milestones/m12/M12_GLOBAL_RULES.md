---
Title: Milestone 12 — Global Rules
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: M12
Related Documents:
  - docs/milestones/m11y/RELEASE_CHECKLIST.md
  - docs/milestones/m12/BRANDING_PACKAGING_MATRIX.md
  - docs/PROJECT_BIBLE.md
---

# Milestone 12 — Global Rules

**Production engineering milestone.** Packaging, branding, release artifacts, and production hardening — **not** product UX redesign.

---

## 1. Scope boundaries (non‑negotiable)

| Rule | Meaning |
|------|---------|
| **No Desktop UI redesign** | Do not change layouts, navigation, workflows, or manually improved screens. |
| **No Flutter UI redesign** | Same constraint for mobile — no layout or workflow changes. |
| **Extend only** | Add packaging scripts, assets, build config, env gates, CI release jobs. Do not rewrite completed modules. |
| **Backward compatible** | Existing APIs, DB data, settings, and client behaviour must keep working after upgrade. |

### Preserved systems (do not refactor)

- Desktop application (Electron + React)
- Flutter application
- Backend architecture
- RBAC
- Backup system
- Tally integration
- AI integration
- Networking / mDNS discovery
- Business logic
- Database structure *(Alembic migrations only when strictly required)*

---

## 2. Schema & migrations

- All schema changes **must** ship with safe, reversible Alembic migrations.
- No destructive migrations without explicit ADR and ops sign-off.
- Clients must tolerate one-version-behind API during rolling upgrades.

---

## 3. Release artifacts (only these)

| Platform | Required artifact | Notes |
|----------|-------------------|--------|
| **Windows Desktop** | `WEBSTUDIO Desktop Setup.exe` | NSIS or equivalent branded installer |
| **macOS Desktop** | `WEBSTUDIO Desktop.dmg` | Signed/notarized when certs available |
| **Android** | `WEBSTUDIO IMS.apk` | Release-signed APK |
| **iOS** | Xcode project configured for **Release / IPA generation** | No App Store listing assets |

### Explicitly out of scope

- Play Store listing (screenshots, feature graphic, store description)
- App Store Connect marketing assets
- In-app purchase / subscription setup
- Public store submission automation

---

## 4. Branding requirements

**Identity:** **WEBSTUDIO Dark Logo** on **white background** everywhere installer and OS shell branding appear.

Replace **all** default Electron, Flutter, and installer placeholder assets.

| Surface | Platform |
|---------|----------|
| Windows EXE installer | Desktop |
| macOS DMG | Desktop |
| Desktop app icon | Desktop |
| Taskbar / tray icon | Desktop |
| Start Menu icon | Desktop |
| Splash screen | Desktop |
| About screen | Desktop |
| Android launcher icon | Flutter |
| Android splash | Flutter |
| iOS app icon | Flutter |
| iOS launch screen | Flutter |
| Installer graphics | Desktop |
| Uninstaller | Desktop |
| Version information (file/product metadata) | Desktop |

**Canonical asset registry:** `apps/desktop/public/assets/webstudio/` — see [README](../../../apps/desktop/public/assets/webstudio/README.md).

No placeholder Flutter or Electron branding may remain in release builds.

---

## 5. Engineering principles for M12 work

1. **Configuration over code** — prefer `electron-builder.yml`, Gradle signing, Xcode build settings, env files.
2. **Scripts over refactors** — `scripts/release/` for repeatable builds; no business-logic changes.
3. **Document every gate** — signing, notarization, keystore, version bump in [RELEASE_CHECKLIST.md](../m11y/RELEASE_CHECKLIST.md).
4. **CI produces artifacts** — `.github/workflows/release.yml` on version tag (when certs are configured).
5. **Test packaged builds** — checklist items F1–F2 in release checklist.

---

## 6. Agent / developer checklist before any M12 PR

- [ ] Does this change any screen layout or user workflow? → **Reject** (unless pure branding asset swap in existing slot)
- [ ] Does this rewrite an existing service module? → **Extend** instead
- [ ] Does this add a DB change? → **Migration required**
- [ ] Does this add a new release artifact type? → **Out of scope** unless approved
- [ ] Are branding assets sourced from `assets/webstudio/` registry? → **Required**

---

## 7. Handoff from Milestone 11Y

M11Y verdict: **READY FOR MILESTONE 12** (packaging), not customer release.

Open M12 entry items: packaging infrastructure (D1–D11), CI release workflow (E5), branded icons (D10), production demo gate (B4).

See [FINAL_ENGINEERING_SIGNOFF.md](../m11y/FINAL_ENGINEERING_SIGNOFF.md).
