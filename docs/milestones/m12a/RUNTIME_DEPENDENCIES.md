---
Title: Runtime Dependencies
Version: 1.0.0
Status: Final — Awaiting Review
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12A
---

# Runtime Dependencies — Production Packaging Audit

**Purpose:** Inventory what must be present on operator, server, and client machines at runtime. Distinct from dev/build tooling.

---

## Summary matrix

| Component | Runtime requirement | Shipped in artifact? |
|-----------|---------------------|----------------------|
| PostgreSQL | 15+ (extensions: pg_trgm, pgcrypto) | No — operator installs |
| Python backend | 3.12+ + pip packages | Bundled via venv or future installer |
| Desktop | Electron 33.x + Chromium | Bundled in Setup.exe / DMG |
| Android | Android 8+ (API 26+) | APK is self-contained |
| iOS | iOS 13+ | IPA + App Store / enterprise install |
| Tally ERP 9 | LAN XML port (optional integration) | External |

---

## Backend (Python)

**Source:** `apps/backend/pyproject.toml`

| Package | Min version | Runtime role |
|---------|-------------|--------------|
| python | ≥3.12 | Interpreter |
| fastapi | ≥0.115.0 | HTTP API |
| uvicorn[standard] | ≥0.32.0 | ASGI server |
| sqlalchemy[asyncio] | ≥2.0.36 | ORM |
| asyncpg | ≥0.30.0 | PostgreSQL async driver |
| alembic | ≥1.14.0 | Migrations (deploy-time) |
| pydantic-settings | ≥2.6.0 | Configuration |
| PyJWT | ≥2.9.0 | JWT auth |
| argon2-cffi | ≥23.1.0 | Password hashing |
| httpx | ≥0.28.0 | Outbound HTTP (Tally, etc.) |
| zeroconf | ≥0.132.0 | mDNS discovery |
| cryptography | ≥43.0.0 | Field encryption |
| python-multipart | ≥0.0.12 | File uploads |
| loguru | ≥0.7.2 | Logging |
| openpyxl | ≥3.1.5 | Excel export |
| defusedxml | ≥0.7.1 | Safe Tally XML parse |

**Gap:** No lockfile — production installs may resolve different transitive versions over time. **M12 recommendation:** generate `requirements.lock` or use `uv lock`.

**Process model:** Single uvicorn worker recommended for MVP; schedulers (Tally, backup) run in-process via FastAPI lifespan.

---

## Desktop (Node / Electron)

**Source:** `apps/desktop/package.json`, root workspace

### Shipped (production bundle)

| Dependency | Version (approx.) | Role |
|------------|-----------------|------|
| electron | ^33.x | Shell |
| react / react-dom | 19.x | UI |
| react-router-dom | 7.x | Routing |
| zustand | 5.x | State |
| @webstudio/api-client | workspace | API |
| @webstudio/shared-kernel | workspace | Types |
| @webstudio/ui-components | workspace | UI |
| @webstudio/auth | workspace | Auth helpers |

### Not shipped (dev/build only)

| Tool | Notes |
|------|-------|
| vite | Bundler — output is static assets |
| typescript | Compile-time |
| vitest / testing-library | Tests |
| electron-vite or vite plugin | Build |

**Security note:** `pnpm audit` reported 23 advisories (2026-07-02); most affect dev toolchain. Upgrade Vite ≥6.4.3 and Electron patch before release CI hardening.

---

## Flutter (Mobile)

**Source:** `apps/mobile_flutter/pubspec.yaml`

| Package | Role |
|---------|------|
| flutter (SDK) | Framework |
| flutter_riverpod | State |
| go_router | Navigation |
| dio | HTTP |
| shared_preferences | Saved API URL |
| connectivity_plus | Network status |
| mobile_scanner | QR onboarding |
| package_info_plus | Version / update gate |
| flutter_secure_storage | Token storage |
| intl | Formatting |

**Platform embedders:**

| Platform | Min SDK | Notes |
|----------|---------|-------|
| Android | compileSdk 35, minSdk 26 | Release signing **must** change from debug |
| iOS | Deployment target 13.0 | Requires Apple dev/distribution certs |

---

## PostgreSQL

| Requirement | Detail |
|-------------|--------|
| Version | 15+ recommended |
| Extensions | `pg_trgm`, `pgcrypto` (created by migrations) |
| Schema | `webstudio` |
| Connection | `DATABASE_URL` async URL for app; sync URL for Alembic |

**Docker dev:** `compose.yaml` — `postgres:16-alpine`, port 5432.

---

## Shared TypeScript packages (desktop-only runtime)

| Package | Path | Consumed by |
|---------|------|-------------|
| `@webstudio/api-client` | `packages/api-client` | Desktop |
| `@webstudio/auth` | `packages/auth` | Desktop |
| `@webstudio/shared-kernel` | `packages/shared-kernel` | Desktop |
| `@webstudio/ui-components` | `packages/ui-components` | Desktop |

Flutter does **not** consume TS packages — parallel Dart implementation.

---

## External / optional integrations

| System | Protocol | Runtime dependency |
|--------|----------|-------------------|
| Tally ERP 9 | HTTP XML on LAN | Tally must be running; no Tally binaries in IMS |
| Excel | File export/import | openpyxl server-side; desktop opens via OS |
| mDNS | UDP 5353 | Zeroconf on server for discovery |

---

## OS-level dependencies (server — Windows)

Per deployment documentation:

| Component | Purpose |
|-----------|---------|
| Python 3.12+ | Backend |
| PostgreSQL 15+ | Database |
| NSSM or Windows Service wrapper | Optional — keep API running |
| OpenSSL / cert store | TLS termination (if not behind reverse proxy) |

**Not bundled today:** Installer must document or script these prerequisites.

---

## Reproducibility gaps (M12 targets)

| Gap | Risk | Mitigation |
|-----|------|------------|
| No Python lockfile | Drift between installs | Lock in M12 |
| No `pnpm deploy` / frozen lockfile in CI release | Rare desktop drift | `pnpm install --frozen-lockfile` in release job |
| Flutter no FVM pin in repo | CI/local SDK mismatch | Document Flutter 3.24+ channel in release checklist |
| Electron not pinned in release workflow | — | Pin exact Electron in builder config |

---

## Related documents

- [M11Y Dependency Audit](../m11y/DEPENDENCY_AUDIT.md)
- [TECH_STACK.md](../../TECH_STACK.md)
- [PRODUCTION_ENVIRONMENT_CONFIGURATION.md](./PRODUCTION_ENVIRONMENT_CONFIGURATION.md)
