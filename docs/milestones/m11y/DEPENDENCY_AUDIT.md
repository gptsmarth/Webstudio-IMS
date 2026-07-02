---
Title: Dependency Audit
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 11Y
---

# Dependency Audit

**Audit date:** 2026-07-02  
**Method:** Manifest review, `pnpm audit`, codebase grep, Milestone 11 known issues cross-reference.

---

## Summary

| Ecosystem | Packages (approx.) | Vulnerabilities | Unused / duplicate | Recommendation |
|-----------|-------------------|-----------------|--------------------|----------------|
| Node (pnpm workspace) | 8 workspace packages | **23** (1 critical, 5 high) | Legacy `apps/mobile` RN stack | Upgrade Vite/Electron; remove RN app |
| Python (backend) | 18 runtime deps | Not scanned (no lockfile) | None critical | Add `pip-audit` to CI |
| Flutter | ~30 direct deps | Not scanned | None identified | Run `flutter pub outdated` in M12 |

---

## Node / pnpm Workspace

### Workspace packages

| Package | Purpose | Used in production? |
|---------|---------|---------------------|
| `@webstudio/desktop` | Electron client | ✅ |
| `@webstudio/shared-kernel` | Shared types | ✅ |
| `@webstudio/api-client` | HTTP client | ✅ |
| `@webstudio/ui-components` | UI primitives | ✅ |
| `@webstudio/auth` | Auth helpers | ✅ Desktop/mobile |
| `@webstudio/testing` | Test utilities | Dev only |
| `apps/mobile` (RN) | Legacy stub | ❌ **Remove** |

### `pnpm audit` (2026-07-02)

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 5 |
| Moderate | 13 |
| Low | 4 |
| **Total** | **23** |

**Notable paths:**

| Package | Issue | Affected | Recommendation |
|---------|-------|----------|----------------|
| `vite` ≤6.4.2 | GHSA-fx2h-pf6j-xcff | Desktop dev/build | Upgrade to ≥6.4.3 or pin patched 5.x when available |
| `electron` | Historical advisories | Desktop shell | Stay on latest 33.x patch in M12 |
| Transitive deps | Moderate/low | RN legacy tree | Remove `apps/mobile` to reduce surface |

**Note:** Most findings affect **development/build** tooling, not shipped renderer code. Still resolve before release engineering hardens CI.

### Duplicate / overlapping packages

| Area | Finding |
|------|---------|
| Mobile clients | **Two mobile apps** — Flutter (active) + React Native (legacy) |
| HTTP clients | Desktop uses `@webstudio/api-client`; some exports still used raw `fetch` historically (fixed for audit/security exports) |
| State management | Desktop Zustand; Flutter Riverpod — intentional per platform |

### Deprecated libraries

| Library | Status |
|---------|--------|
| React Native in `apps/mobile` | Superseded — deprecate workspace entry |
| None critical in active Flutter/desktop deps | — |

---

## Python / Backend

### Runtime dependencies (`pyproject.toml`)

| Package | Version constraint | Role |
|---------|-------------------|------|
| fastapi | ≥0.115.0 | API framework |
| uvicorn | ≥0.32.0 | ASGI server |
| sqlalchemy | ≥2.0.36 | ORM |
| asyncpg | ≥0.30.0 | PostgreSQL driver |
| alembic | ≥1.14.0 | Migrations |
| PyJWT | ≥2.9.0 | Auth tokens |
| argon2-cffi | ≥23.1.0 | Password hashing |
| httpx | ≥0.28.0 | HTTP client |
| zeroconf | ≥0.132.0 | mDNS (11X) |
| cryptography | ≥43.0.0 | Secret encryption |

### Observations

| Item | Recommendation |
|------|----------------|
| No `requirements.lock` / poetry lock | Add lockfile or pip-tools pin for reproducible server builds in M12 |
| Minimum-version pins only | Run `pip-audit` in CI against locked env |
| Dev deps (pytest, ruff, mypy) | Appropriate; keep separate from production image |

### Unused packages

No unused **runtime** Python packages identified in `pyproject.toml`.

---

## Flutter (`apps/mobile_flutter`)

### Key production dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| flutter_riverpod | ^2.6.1 | State |
| dio | ^5.7.0 | HTTP |
| flutter_secure_storage | ^9.2.4 | Token storage |
| bonsoir | ^5.1.3 | mDNS discovery (11X) |
| hive / hive_flutter | ^2.2.3 / ^1.1.0 | Offline queue |
| mobile_scanner | ^7.2.0 | Barcode |
| connectivity_plus | ^6.1.1 | Network status |

### Recommendations

| Priority | Action |
|----------|--------|
| M12 | Add `flutter_launcher_icons` for branded APK/IPA icons |
| M12 | Configure release signing (keystore / provisioning profiles) |
| Low | Run `flutter pub outdated` and plan safe minor upgrades |

---

## Desktop-specific additions (11X)

| Package | Version | Purpose |
|---------|---------|---------|
| bonjour-service | ^1.2.1 | mDNS browse in Electron main |

---

## Version Conflicts

| Conflict | Impact | Resolution |
|----------|--------|------------|
| React Native peer (`react-native` ≥0.82 vs 0.76.5 in legacy app) | Legacy app only | Remove `apps/mobile` |
| Vite 5.x vs advisory patch 6.4.3 | Build-time | Plan coordinated upgrade in M12 |

---

## CI Recommendations (M12)

1. Enable `pnpm audit --audit-level=high` in CI (fail on critical/high in production dependency tree).
2. Add `pip-audit` for backend Docker image build.
3. Add Dependabot or Renovate for automated PRs.
4. Exclude legacy `apps/mobile` from audit scope until removed.

---

## Action Summary

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Remove or isolate `apps/mobile` from workspace | M12 |
| P1 | Upgrade Vite / address critical npm advisory | M12 |
| P1 | Python dependency lockfile + pip-audit | M12 |
| P2 | Flutter pub outdated review | M12 |
| P2 | shared-kernel / api-client unit tests | Backlog |
