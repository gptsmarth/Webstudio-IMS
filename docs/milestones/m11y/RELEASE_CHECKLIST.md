---
Title: Release Checklist
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11Y → M12 handoff
---

# Release Checklist — Pre-Packaging Gate

Use this checklist at the **start of Milestone 12** and again **before customer release**.

Legend: ✅ Done (11Y) | ⏳ M12 | 🔲 Pending | ⚠️ Conditional

---

## A. Codebase Quality (11Y verified)

| # | Item | Status |
|---|------|--------|
| A1 | No Critical known issues in application code | ✅ |
| A2 | Desktop TypeScript clean (`pnpm typecheck`) | ✅ |
| A3 | Desktop unit tests pass | ✅ 95/95 |
| A4 | Flutter tests pass | ✅ 121/121 |
| A5 | Backend network discovery tests pass | ✅ 9/9 |
| A6 | Backend full pytest green in CI | 🔲 Requires DB + fixture fixes |
| A7 | No TODO/FIXME in backend `src/` | ✅ |
| A8 | mDNS discovery implemented (11X) | ✅ |
| A9 | Tally connectivity hardening (M12 prereq) | ✅ |

---

## B. Security & Production Hardening

| # | Item | Status |
|---|------|--------|
| B1 | `APP_ENV=production` documented | ✅ |
| B2 | JWT_SECRET ≥32 bytes enforced at startup | ✅ |
| B3 | `.env` not in git | ✅ |
| B4 | Demo/Preview mode gated in production builds | 🔲 **11Y-H01** |
| B5 | CORS origins configured for deployment | ⏳ Env per site |
| B6 | TLS certificates configured (if terminating on server) | ⏳ |
| B7 | Rate limiting implemented or explicitly waived | 🔲 Flag only |
| B8 | Electron CSP configured | 🔲 |
| B9 | Backup import size limit | 🔲 SEC-002 |
| B10 | Product image magic-byte validation | 🔲 SEC-001 |

---

## C. Version & Compatibility

| # | Item | Status |
|---|------|--------|
| C1 | Version matrix documented | ✅ [VERSION_MATRIX.md](./VERSION_MATRIX.md) |
| C2 | Semver aligned at 0.1.0 | ✅ |
| C3 | Unified release bump script | ⏳ M12 |
| C4 | Build metadata injection (git commit, build date) | ⏳ M12 |
| C5 | Desktop boot version compatibility check | 🔲 |
| C6 | Flutter mandatory update gate | ✅ |
| C7 | Alembic at head before server start | ✅ Process |

---

## D. Packaging Infrastructure (M12)

| # | Item | Status |
|---|------|--------|
| D1 | electron-builder (or equivalent) for Windows | ⏳ |
| D2 | electron-builder DMG for macOS | ⏳ |
| D3 | Windows code signing certificate | ⏳ |
| D4 | macOS notarization pipeline | ⏳ |
| D5 | Android release keystore + signing config | ⏳ |
| D6 | iOS provisioning + distribution cert | ⏳ |
| D7 | `flutter build apk/appbundle --release` script | ⏳ |
| D8 | `flutter build ipa` / Xcode archive script | ⏳ |
| D9 | Server installer / Windows Service wrapper | ⏳ |
| D10 | Branded launcher icons (not Flutter template) | ⏳ |
| D11 | Bundle ID alignment (Android/iOS) | ⏳ |

---

## E. CI/CD (M12)

| # | Item | Status |
|---|------|--------|
| E1 | `ci-backend.yml` runs pytest + ruff | 🔲 Placeholder |
| E2 | `ci-desktop.yml` runs typecheck + vitest + build | 🔲 Placeholder |
| E3 | `ci-mobile.yml` runs flutter analyze + test | 🔲 Placeholder |
| E4 | `ci-database.yml` migration smoke | 🔲 Placeholder |
| E5 | `release.yml` builds artifacts on tag | 🔲 Placeholder |
| E6 | `security-scan.yml` dependency audit | 🔲 Placeholder |
| E7 | Artifact upload + checksums | ⏳ |

---

## F. Staging Acceptance (Manual)

| # | Item | Status |
|---|------|--------|
| F1 | Fresh install: server + DB + setup wizard | 🔲 |
| F2 | Fresh install: desktop packaged build | 🔲 |
| F3 | Fresh install: mobile on physical device | 🔲 |
| F4 | mDNS discovery on office LAN | 🔲 |
| F5 | Upgrade path: app reinstall over existing DB | 🔲 |
| F6 | Backup → restore drill | 🔲 |
| F7 | Role matrix walkthrough (desktop + mobile) | 🔲 |
| F8 | Tally sync on staging LAN | 🔲 |
| F9 | Offline mobile sync stress test | 🔲 |

---

## G. Documentation

| # | Item | Status |
|---|------|--------|
| G1 | Production deployment guide current | ✅ |
| G2 | Network discovery docs (11X) | ✅ |
| G3 | OpenAPI spec matches implementation | 🔲 Placeholder |
| G4 | Remove legacy RN references from TECH_STACK | 🔲 |
| G5 | Release notes template | ⏳ M12 |

---

## H. Sign-Off

| Role | M12 entry (packaging start) | Customer release |
|------|----------------------------|------------------|
| Engineering | See [FINAL_ENGINEERING_SIGNOFF.md](./FINAL_ENGINEERING_SIGNOFF.md) | After F1–F9 + D1–D11 |
| QA | Desktop + Flutter automated ✅ | Staging drills required |
| Security | LAN baseline ✅ | B4–B10 closed |
| Operations | Install docs ✅ | Server installer + monitoring |

---

## Quick Reference — Commands

```bash
# Desktop
cd apps/desktop && pnpm typecheck && pnpm test && pnpm build

# Flutter
cd apps/mobile_flutter && flutter analyze && flutter test

# Backend (requires PostgreSQL)
cd apps/backend && pytest -q

# Backend discovery only
cd apps/backend && pytest tests/test_network_discovery.py -q
```
