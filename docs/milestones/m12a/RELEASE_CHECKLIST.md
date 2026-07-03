---
Title: Release Checklist — M12A Pre-Packaging Gate
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Release Checklist — Milestone 12A

**Purpose:** Gate checklist before **starting M12 packaging implementation** and before **shipping first customer artifacts**. Split into Phase A (audit complete) and Phase B (first release).

---

## Phase A — M12A audit gate (this milestone)

### Documentation

- [x] Production Packaging Report generated
- [x] Folder Structure documented
- [x] Runtime Dependencies documented
- [x] Version Strategy documented
- [x] Upgrade Strategy documented
- [x] Rollback Strategy documented
- [x] Production Environment Configuration documented
- [x] Logging Strategy documented
- [x] Release Checklist (this document) generated
- [ ] **Stakeholder review of M12A reports** ← **WAIT HERE**

### Audit confirmations (read-only)

- [x] No code changes in M12A
- [x] M12 global rules acknowledged ([M12_GLOBAL_RULES.md](../m12/M12_GLOBAL_RULES.md))
- [x] M11Y signoff referenced as functional baseline
- [x] Alembic head recorded as **0034_tally_incremental_sync**
- [x] Critical blockers P-01 through P-10 documented

---

## Phase B — Pre-first-artifact (M12 implementation)

### Version & metadata

- [ ] Single bump script updates root, desktop, Flutter, OpenAPI info
- [ ] Remove `0.1.0-mvp` hardcode from Electron main
- [ ] Git tag convention documented (`v0.1.0`)
- [ ] VERSION_MATRIX updated (migration 0034, artifact list)

### Backend / server

- [ ] Python lockfile or reproducible install documented
- [ ] `.env.example` complete vs `config.py`
- [ ] `pip-audit` in CI (or documented manual run)
- [ ] Staging smoke: `/health`, `/api/v1/version`, login, Tally status
- [ ] Pre-release backup script verified on staging

### Desktop (Electron)

- [ ] `electron-builder` configured (NSIS + DMG)
- [ ] `icon.ico` / `icon.icns` wired from `public/assets/webstudio/`
- [ ] WEBSTUDIO dark logo on white installer/splash per branding matrix
- [ ] Preview/demo mode **disabled** in production build
- [ ] Renderer CSP evaluated and applied
- [ ] Code signing cert (Windows/macOS) or documented unsigned dev channel
- [ ] `pnpm audit` critical/high resolved or accepted with waiver
- [ ] Install → launch → login → logout smoke on Win + macOS

### Flutter (mobile)

- [ ] Android release keystore created (not debug)
- [ ] `build.gradle.kts` release signing configured
- [ ] iOS bundle ID aligned with Android namespace decision
- [ ] Launcher icons generated from webstudio registry
- [ ] Native splash (white + logo-dark) configured
- [ ] Release scripts: `build apk --release`, iOS archive documented
- [ ] Mandatory update gate tested against raised `min_client_version`
- [ ] QR onboarding + API discovery smoke on physical device

### CI / release engineering

- [ ] `release.yml` builds on version tag
- [ ] Artifacts uploaded (Setup.exe, DMG, APK, IPA or export)
- [ ] SHA256 checksums published
- [ ] N-1 artifact retention on internal share
- [ ] Release notes template per version

### Security

- [ ] No secrets in artifacts or repo
- [ ] Demo mode gated (11Y-H01)
- [ ] JWT production gate tested
- [ ] Signing keys in CI secrets only

### QA / staging acceptance

- [ ] Full upgrade drill: N → N+1 on staging DB copy
- [ ] Rollback drill: restore pre-upgrade dump
- [ ] Tally incremental sync during/after upgrade
- [ ] Desktop + Flutter against staging production-config API
- [ ] JSON logs verified parseable

### Operations

- [ ] DEPLOY-001 cross-check with actual env var names
- [ ] Operator quick-start for first install + upgrade
- [ ] Support playbook: collect desktop log + server stdout
- [ ] Known issues doc updated for release

---

## Phase C — Customer ship gate (first GA)

- [ ] All Phase B items complete or waived with sign-off
- [ ] Engineering sign-off
- [ ] QA sign-off
- [ ] Security sign-off (demo gate, signing, dependencies)
- [ ] Operations sign-off (backup/restore drill within 30 days)
- [ ] Release notes published
- [ ] Tagged release in Git
- [ ] Artifacts distributed through approved channel

---

## Smoke test script (minimal)

Run after any packaging change:

| # | Step | Pass criteria |
|---|------|---------------|
| 1 | Server `alembic current` | Head = expected revision |
| 2 | GET `/health` | 200 |
| 3 | GET `/api/v1/version` | SemVer matches tag |
| 4 | Admin login | Token issued |
| 5 | List inventory SKU | 200 + data |
| 6 | Desktop connect + login | Dashboard loads |
| 7 | Flutter connect + login | Home loads |
| 8 | Tally dashboard (if licensed) | Operational block renders |
| 9 | Create backup (if enabled) | Job completes |
| 10 | Check server log line | Valid JSON in production mode |

---

## Waiver template

For items deferred post-MVP:

| Item ID | Reason | Risk | Approver | Expiry |
|---------|--------|------|----------|--------|
| e.g. P-09 | Dev-only CVE | Low | Security | Next patch |

---

## Current status summary

| Phase | Status |
|-------|--------|
| **Phase A (M12A audit)** | **Complete — awaiting review** |
| Phase B (packaging) | Not started |
| Phase C (customer GA) | Not started |

---

## Related documents

- [PRODUCTION_PACKAGING_REPORT.md](./PRODUCTION_PACKAGING_REPORT.md)
- [M12 Global Rules](../m12/M12_GLOBAL_RULES.md)
- [M11Y Release Checklist](../m11y/RELEASE_CHECKLIST.md)
- [Branding Matrix](../m12/BRANDING_PACKAGING_MATRIX.md)
