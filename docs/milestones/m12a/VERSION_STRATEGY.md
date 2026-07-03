---
Title: Version Strategy
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Version Strategy — Production Packaging Audit

**Purpose:** Define how version numbers are assigned, propagated, and enforced across server, desktop, and mobile before and during M12 packaging.

---

## Current state (2026-07-02)

| Artifact | Location | Version | Build metadata |
|----------|----------|---------|----------------|
| Monorepo root | `package.json` | `0.1.0` | — |
| Desktop app | `apps/desktop/package.json` | `0.1.0` | — |
| Electron main | `electron/main.ts` | `0.1.0-mvp` | **Hardcoded — drift** |
| Flutter | `pubspec.yaml` | `0.1.0+1` | `+1` = Android versionCode / iOS build |
| Backend | No single version file | — | `/api/v1/version` returns configured values |
| Database | Alembic | **34 migrations** | Head: `0034_tally_incremental_sync` |
| VERSION_MATRIX (M11Y) | docs | Stale | Lists migration 0033 — update in M12 |

**Assessment:** Semantic alignment at **0.1.0** is intentional for MVP; **injection and single source of truth are missing**.

---

## Recommended versioning scheme

### Semantic versioning (SemVer)

Format: **`MAJOR.MINOR.PATCH`**

| Bump | When |
|------|------|
| MAJOR | Breaking API or incompatible DB migration requiring coordinated client upgrade |
| MINOR | New features, backward-compatible API/DB |
| PATCH | Bug fixes, no schema change |

**Pre-1.0 rule:** While `0.x`, MINOR may include breaking changes with explicit release notes and migration guides.

### Flutter build number

Format: **`VERSION+BUILD`** (e.g. `0.1.0+1`)

| Field | Maps to |
|-------|---------|
| `0.1.0` | User-visible versionName (Android) / CFBundleShortVersionString (iOS) |
| `+1` | monotonic `versionCode` / CFBundleVersion |

**Rule:** Increment BUILD on every store/sideload release; increment PATCH/MINOR per SemVer above.

### Desktop / Electron

- **Product version:** Same SemVer as monorepo (e.g. `0.1.0`)
- **File version / build id:** CI run number or git short SHA suffix for support (`0.1.0+build.4821a3f`)
- **Remove** `-mvp` suffix for production channels

### Backend API version

Expose via **`GET /api/v1/version`**:

| Field | Purpose |
|-------|---------|
| `version` | Server release SemVer |
| `min_client_version` | Advisory floor (Flutter enforces mandatory update) |
| `schema_revision` | Optional Alembic head label for support |

**Database migrations** are versioned independently via Alembic revision IDs — not user-facing SemVer.

---

## Single source of truth (M12 target)

```
VERSION (root file or package.json)
    │
    ├── scripts/bump-version.sh
    │       ├── apps/desktop/package.json
    │       ├── apps/mobile_flutter/pubspec.yaml
    │       ├── electron-builder config
    │       └── backend settings default / openapi info
    │
    └── Git tag v0.1.0 triggers release.yml
```

**Recommendation:** Add root `VERSION` file or use `package.json` version with automated sync script — **do not** hand-edit four locations.

---

## Client–server compatibility

| Client | Enforcement today | M12 target |
|--------|-------------------|------------|
| Flutter | Hard gate vs `min_client_version` | Keep; document in release notes |
| Desktop | None | Soft banner or block below min (optional M12+) |
| API | OpenAPI v1 stable within minor | Document breaking changes in MAJOR |

**Rule:** Any migration that requires new client behavior ships with bumped `min_client_version` and coordinated artifact release.

---

## Git tagging

| Tag pattern | Meaning |
|-------------|---------|
| `v0.1.0` | Release candidate / GA for that version |
| `v0.1.0-rc.1` | Optional pre-release |

**CI:** `release.yml` triggers on `v*.*.*` tags only (not every main commit).

---

## Channel strategy (post-MVP)

| Channel | Audience | Version example |
|---------|----------|-----------------|
| stable | Production customers | `0.1.0` |
| beta | Early adopters | `0.2.0-beta.1` |
| internal | QA | `0.2.0-dev.<sha>` |

M12 MVP: **stable channel only** — no auto-update server required; manual installer distribution.

---

## Documentation versioning

| Doc | Rule |
|-----|------|
| ADR / specs | Reference SemVer + migration ID in commits |
| VERSION_MATRIX | Update on every release with Alembic head |
| Release notes | Per artifact under `docs/milestones/m12/releases/` (create in M12) |

---

## Action items for M12 implementation

1. Remove hardcoded `0.1.0-mvp` from `electron/main.ts` — inject at build
2. Sync Flutter `+BUILD` in bump script
3. Update VERSION_MATRIX to migration **0034**
4. Add OpenAPI `info.version` sync from root version
5. Document version bump in [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md)

---

## Related documents

- [UPGRADE_STRATEGY.md](./UPGRADE_STRATEGY.md)
- [M11Y VERSION_MATRIX.md](../m11y/VERSION_MATRIX.md)
- [M12 Global Rules](../m12/M12_GLOBAL_RULES.md) — C3/C4
