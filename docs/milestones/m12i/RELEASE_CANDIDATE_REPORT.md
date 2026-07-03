---
Title: Release Candidate Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12I
Release: 0.1.0-rc
---

# Release Candidate Report — v0.1.0

**Candidate tag:** `v0.1.0`  
**Build date:** 2026-07-02  
**Git discipline:** Manifest records commit at bundle time (`scripts/release/lib/generate_manifest.py`)

---

## RC scope

This release candidate bundles all Milestone 12 deliverables:

| Milestone | Scope |
|-----------|-------|
| M12A | Production packaging strategy, folder structure, logging |
| M12B | Windows service, business-hours deployment |
| M12C | Desktop/mobile/server installers |
| M12D | Network deployment reports |
| M12E | Enterprise Tally deployment |
| M12F | Office Deployment Wizard |
| M12G | Release engineering (manifest, checksums, CI) |
| M12H | Production documentation pack (21 guides) |
| M12I | Final validation (this report) |

---

## Artifact manifest

Expected artifacts per `release/v0.1.0/version-manifest.json`:

| Artifact | Platform | Build command |
|----------|----------|---------------|
| `WEBSTUDIO Desktop Setup.exe` | Windows desktop | `pnpm desktop:package:win` |
| `WEBSTUDIO Desktop.dmg` | macOS desktop | `pnpm desktop:package:mac` |
| `WEBSTUDIO-Android.apk` | Android | `flutter build apk` |
| `WEBSTUDIO.aab` | Android (Play) | `flutter build appbundle` |
| `WEBSTUDIO-Server-Setup.exe` | Windows server | Inno Setup compile |
| `migrations/` | Database | `scripts/release/package-migrations.sh` |
| `checksums.sha256` | Integrity | `scripts/release/generate-checksums.sh` |
| `RELEASE_NOTES.md` | Documentation | `scripts/release/generate-release-notes.sh` |

**Bundle assembly:** `bash scripts/release/prepare-release.sh`

---

## Automated test evidence

Executed 2026-07-02 on validation host (macOS, Python 3.13.7, Node 20, Flutter stable).

| Suite | Command | Result | Duration |
|-------|---------|--------|----------|
| Backend | `pytest` (apps/backend) | **346 passed**, 2 skipped | 75.8s |
| Desktop | `pnpm test` (apps/desktop) | **95 passed** | 0.7s |
| Mobile | `flutter test` (apps/mobile_flutter) | **121 passed** | 7.6s |

### Backend coverage by domain

| Domain | Tests (approx.) | Status |
|--------|-----------------|--------|
| Auth & permissions | 50+ | ✅ |
| Inventory & sales | 40+ | ✅ |
| Tally integration | 25 | ✅ |
| Backup / restore / DR | 30+ | ✅ |
| Reports | 13 | ✅ |
| Notifications | 17 | ✅ |
| Office deployment | 3 | ✅ |
| Network discovery | 9 | ✅ |
| AI / product enrichment | 30+ | ✅ |
| Migrations (schema) | 6 | ✅ |

### Skipped tests

| Test | Reason |
|------|--------|
| 2 skipped | Environment-conditional (documented in test modules) |

---

## M12I corrections included in RC

| ID | Issue | Resolution |
|----|-------|------------|
| M12I-001 | 6 migration tests failed (stale revision whitelist) | `assert_at_least_migration()` helper |
| M12I-002 | 27+ pytest errors (DB session / event loop) | AsyncClient + lifespan test guards |
| M12I-003 | AI enrichment tests hung on web scrape | Skip `resolve_product_image` when `is_test` |
| M12I-004 | 30s graceful shutdown per test app teardown | Production-only graceful shutdown |

---

## Configuration profiles

| Profile | Path | Use |
|---------|------|-----|
| Development | `config/env/.env.development` | Local dev |
| Testing | `config/env/.env.testing` | CI / pytest |
| Staging | `config/env/.env.staging` | Pre-prod LAN |
| Production | `config/env/.env.production` | Customer server |

---

## Database upgrade path

1. Stop Windows service (or uvicorn) gracefully.
2. Backup database via Admin → Backup or `pg_dump`.
3. Apply migrations: `bash tools/scripts/alembic.sh upgrade head`
4. Verify: `SELECT version_num FROM webstudio.alembic_version` → `0036_tally_probe_scheduler`
5. Start service; confirm `/health/live` and Office Deployment Wizard summary.

---

## RC acceptance criteria

| Criterion | RC status |
|-----------|-----------|
| All automated tests green | ✅ |
| Installers build from documented commands | ✅ (CI + local scripts) |
| Checksums generated for bundle | ✅ |
| Production docs complete (M12H) | ✅ |
| Staging LAN drill | ⏳ Pending |
| Signed installers | ⏳ Pending certificates |

---

## Recommendation

**Approve Release Candidate `0.1.0` for staging deployment.**

Promote to **General Availability** only after:

1. Staging acceptance per [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
2. Signed desktop and mobile artifacts
3. Customer pilot sign-off
