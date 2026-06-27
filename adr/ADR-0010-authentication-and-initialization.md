---
Title: ADR-0010 — Authentication and Initialization
Version: 1.0
Status: Accepted
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/PROJECT_BIBLE.md, docs/product/PRODUCT_REQUIREMENTS.md, docs/SYSTEM_ARCHITECTURE.md, docs/database/DATABASE_DESIGN.md, docs/api/API_SPECIFICATION.md
---

# ADR-0010: Authentication and Initialization

| Attribute | Value |
|-----------|-------|
| **ADR ID** | ADR-0010 |
| **Version** | 1.0 |
| **Status** | Accepted |
| **Date** | 2026-06-27 |

---

## Purpose

Record the binding architectural decisions for **server initialization**, **first-time setup**, **user authentication**, **role-based authorization**, and **client onboarding** in WEBSTUDIO IMS Version 1.

This ADR establishes:

- How the system transitions from an empty deployment to an operational state
- Where credentials and user records live
- How clients discover and connect to the Backend
- What authentication mechanisms are in scope — and explicitly excluded — for Version 1

All implementation (Backend API, clients, database migrations, and deployment runbooks) must conform to this ADR and the governing specifications it references.

---

## Decision

WEBSTUDIO IMS Version 1 adopts the following authentication and initialization architecture.

### Server initialization

| Decision | Detail |
|----------|--------|
| **One-time server install** | The Dedicated Server PC is installed once per business deployment. |
| **`system_initialized` flag** | Initialization state is stored as `system_initialized` in `system_settings`. The Backend **must not** infer initialization from Main Admin user existence. |
| **Fresh database seed** | Migrations seed reference data (brands, locations) and `system_initialized = false`. **No Main Admin user is seeded.** |
| **First-Time Setup Wizard** | When `system_initialized = false`, clients present a wizard collecting: Company Name, Main Admin Name, Username, Password, Confirm Password. |
| **Post-setup state** | On success: create exactly one Main Admin; set `system_initialized = true`; persist `company_name`. The wizard must not reappear unless the database is intentionally reinitialized. |
| **Main Admin created only once** | The initial Main Admin is created by `POST /api/v1/setup/initialize` during first-time setup — not by migration seed, installer script, or client-side logic. |

### Authentication authority

| Decision | Detail |
|----------|--------|
| **Backend is the sole authority** | All user accounts, password hashes, roles, and session state live in PostgreSQL, accessed exclusively through the Backend API. |
| **Clients never create users** | Desktop and Android installations connect to the server; they do not provision accounts locally. |
| **Clients never store business data** | Clients persist server HTTPS URL, authentication tokens, and UI preferences only. No inventory, user directory, or audit data is stored locally in Version 1. |
| **Users authenticate against Backend only** | Login, token refresh, and password verification occur server-side. |

### Credentials and passwords

| Decision | Detail |
|----------|--------|
| **bcrypt hashing** | Passwords are stored only as **bcrypt** hashes (cost factor ≥ 12). Plaintext passwords are never persisted, logged, or returned in API responses. |
| **Password reset by Main Admin only** | Main Admin may set a temporary password for any user. Users may change their own password when authenticated. |
| **No self-service recovery** | No email-based password recovery, no OTP, no security questions, and no external identity provider. **Only Main Admin reset** is available in Version 1. |
| **No email** | The system does not send email for authentication or account management. |
| **No OTP / MFA** | One-time passwords and multi-factor authentication are out of scope for Version 1. |

### Roles and user lifecycle

| Decision | Detail |
|----------|--------|
| **Three fixed human roles** | `main_admin`, `admin`, `salesperson` — defined in application code; no custom roles in Version 1. |
| **Main Admin** | Full system access including user management: create users, disable users, reset passwords, assign roles. |
| **Admin** | Inventory and operational management per PRD permission matrix. |
| **Salesperson** | Search, view, and move inventory per PRD permission matrix. Manual mark-as-sold is **Admin and Main Admin only** (see ADR-0011). |
| **Users disabled, not deleted** | User accounts are deactivated (`status = disabled`) rather than permanently deleted. Audit history and referential integrity are preserved. |
| **Service accounts** | Background workers (Excel Sync, Tally Sync) authenticate as dedicated API users with restricted permissions — separate from the three human roles. |

### Transport and tokens

| Decision | Detail |
|----------|--------|
| **HTTPS mandatory (production)** | All client and worker communication with the Backend uses HTTPS on the office LAN. TLS is terminated at the Backend API using an internal CA certificate. |
| **JWT authentication** | Authenticated API requests carry a short-lived **access token** (JWT, default 15 minutes). A **refresh token** (default 7 days, rotatable, stored hashed server-side) renews access without re-entering credentials. |
| **RBAC on every request** | Valid JWT is necessary but not sufficient — every endpoint enforces role and permission checks server-side. |

### Client onboarding

| Decision | Detail |
|----------|--------|
| **Setup status gate** | After connecting to the server, clients call `GET /api/v1/setup/status`. If `system_initialized = true` → Login screen. If `false` → First-Time Setup Wizard. |
| **Automatic server discovery** | On first launch, clients attempt LAN server discovery. |
| **Single server found** | Display server information; require user confirmation. |
| **Multiple servers found** | Present selection list. |
| **Discovery failure** | Automatically fall back to **Manual Server Configuration**: Server HTTPS URL, Test Connection, Save Configuration. |
| **Future discovery protocol** | mDNS / Bonjour or equivalent may be adopted later; Version 1 defines the workflow, not the wire protocol. |

---

## Context

WEBSTUDIO IMS is an on-premise inventory platform for a laptop retail business operating three locations on a shared office Wi-Fi network. Staff use Windows/macOS desktop clients and an Android client; a Dedicated Server PC hosts PostgreSQL, the FastAPI Backend API, and background sync workers.

### Business constraints

- Retail staff require simple login with minimal training — no corporate SSO, no email infrastructure dependency.
- The business has no dedicated IT staff for ongoing identity management.
- Inventory data is commercially sensitive; credentials and business state must not reside on client devices.
- Tally ERP 9 remains the billing system; WEBSTUDIO IMS owns inventory and user identity only.

### Technical constraints

- PostgreSQL is the single source of truth; the Backend API is the only gateway to the database ([PROJECT_BIBLE](../docs/PROJECT_BIBLE.md)).
- Version 1 is online-first: clients do not maintain a local inventory cache or offline mutation queue.
- Deployment is LAN-only with an internal CA — not public internet or cloud identity.

### Problem addressed

Prior documentation referenced seeding a Main Admin user or creating one manually during deployment. That approach was ambiguous (clients could not distinguish fresh install from misconfiguration) and risked duplicate admin provisioning across multiple client installs.

A dedicated `system_initialized` flag, a first-time setup wizard exposed through the API, and a standardized client onboarding flow provide a single, auditable path from empty database to operational system.

---

## Alternatives Considered

### Infer initialization from Main Admin user existence

**Rejected.** Checking whether a `main_admin` row exists couples initialization to user-table state, breaks if the admin is temporarily disabled, and complicates reinitialization. A dedicated `system_initialized` setting is explicit and queryable by unauthenticated setup endpoints.

### Seed a default Main Admin in migrations

**Rejected.** Hardcoded or migration-seeded credentials are a security risk, encourage unchanged default passwords, and bypass the First-Time Setup Wizard business flow. Reference data only is seeded; the operator chooses credentials at setup.

### Client-side user creation during install

**Rejected.** Violates backend authority. Multiple client installs could race to create admins; credentials would not be centrally auditable.

### Argon2id instead of bcrypt

**Deferred.** Argon2id is preferable for greenfield systems but was not the approved Version 1 stack decision. bcrypt (cost ≥ 12) is mandated for Version 1; Argon2id may be evaluated in a future ADR.

### RS256 JWT signing

**Deferred.** HS256 with a server-side secret is sufficient for a single API instance on-premise. RS256 remains an option if multi-service token validation is required later.

### Email-based password recovery

**Rejected.** No business email infrastructure is assumed. Self-service recovery would require email delivery, template management, and token expiry flows outside Version 1 scope.

### OTP / MFA (TOTP, SMS)

**Rejected for Version 1.** Adds enrollment, recovery, and support burden inappropriate for the target operator model. May be reconsidered for Main Admin in a future version.

### External identity provider (OAuth, LDAP, Active Directory)

**Rejected for Version 1.** The deployment environment is a single retail building without enterprise directory services. Local username/password with JWT is sufficient.

### Permanent user deletion

**Rejected.** Disabling accounts preserves audit trail integrity (`created_by_user_id`, `updated_by_user_id`, audit logs) and prevents orphaned references. Reactivation remains a Main Admin capability where needed.

### HTTP on LAN without TLS

**Rejected for production.** HTTPS with an internal CA protects credentials and JWTs on the shared Wi-Fi network. HTTP is permitted on `localhost` for development only.

### Client-side inventory cache with offline login

**Rejected for Version 1.** Online-first architecture; clients do not store business data. Offline queue and cached credentials for inventory are future concerns.

### Manual server URL only (no discovery)

**Rejected as sole approach.** Manual configuration is retained as **fallback** when discovery fails, but automatic discovery reduces installer friction for non-technical staff.

---

## Consequences

### Positive

- **Single initialization path** — operators and developers have one documented flow from install to login.
- **Explicit setup contract** — `GET /api/v1/setup/status` and `POST /api/v1/setup/initialize` are stable integration points for all clients.
- **Centralized identity** — all credential verification, lockout, and role enforcement occur in one place.
- **Auditability** — user management actions and login events are logged server-side; disabled users retain history.
- **Reduced client complexity** — thin clients store tokens and URL only; no local user database or business cache.
- **LAN-appropriate security** — HTTPS + bcrypt + short-lived JWTs provide adequate protection without enterprise IdP overhead.

### Negative / trade-offs

- **No self-service password recovery** — forgotten passwords require Main Admin intervention; operational runbooks must document this.
- **Main Admin lockout risk** — if the sole Main Admin password is lost and no backup admin exists, recovery requires database operator intervention.
- **Online dependency** — staff cannot authenticate or access inventory when the server or LAN is unavailable.
- **Discovery protocol unspecified** — Version 1 workflow is defined; implementation may ship with manual URL first until mDNS/Bonjour is implemented.
- **Fixed role model** — new roles require code changes and PRD amendment; no runtime role editor.

### Compliance with governing documents

This ADR aligns with and is traceable to:

- [PROJECT_BIBLE.md](../docs/PROJECT_BIBLE.md) — §24.4 Server Initialization, §24.5 Client Onboarding, §9 Data Ownership
- [PRODUCT_REQUIREMENTS.md](../docs/product/PRODUCT_REQUIREMENTS.md) — §8.7–§8.10, §15.0, FR-INIT-*, FR-CLIENT-*, FR-AUTH-*, FR-USER-*, BR-28–BR-31
- [SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) — §11 Authentication & Authorization, §20.11 Server Initialization & Client Onboarding
- [DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md) — §4.12 SystemSetting, User entity
- [API_SPECIFICATION.md](../docs/api/API_SPECIFICATION.md) — §2 System Setup, §3 Authentication, §4 Users

---

## Implementation Notes

### Database

- Add `system_initialized` (`boolean`, default `false`) and `company_name` (`string`) to `system_settings` in migration `0009_integrations` (or equivalent).
- `users` table: `username` (unique), `password_hash` (bcrypt), `display_name`, `role` enum (`main_admin`, `admin`, `salesperson`, `service_account`), `status` enum (`active`, `disabled`), lockout fields, `token_version` for session invalidation.
- `refresh_tokens` table: hashed token storage with rotation and reuse detection.
- Seed `system_initialized = false` in migrations; **never** seed a Main Admin user.

### Backend API

| Endpoint | Auth | Behaviour |
|----------|------|-----------|
| `GET /api/v1/setup/status` | None | Returns `system_initialized`, `company_name` |
| `POST /api/v1/setup/initialize` | None (only when `system_initialized = false`) | Creates Main Admin; sets flags; returns `SYSTEM_ALREADY_INITIALIZED` if already done |
| `POST /api/v1/auth/login` | None | Rejects with `SYSTEM_NOT_INITIALIZED` when `system_initialized = false` |
| `POST /api/v1/auth/refresh` | Refresh token body | Standard rotation |
| `POST /api/v1/auth/logout` | Access token | Revokes refresh token |
| `GET /api/v1/auth/me` | Bearer JWT | Current user profile and permissions |
| `GET/POST/PATCH /api/v1/users/*` | Bearer JWT | Main Admin only unless noted |

- Password hashing: `bcrypt` with cost factor ≥ 12 via approved library (e.g., `passlib` or `bcrypt`).
- JWT: access token ~15 min; refresh token ~7 days; permissions embedded at issue time.
- Login rate limiting: 10 attempts/minute per IP (per API specification).

### Clients (Desktop / Android)

1. First launch → server discovery (or manual fallback).
2. Save confirmed HTTPS URL to encrypted local config.
3. `GET /api/v1/setup/status` → route to Setup Wizard or Login.
4. Setup Wizard → `POST /api/v1/setup/initialize` → Login.
5. Login → store refresh token in OS keychain/keystore; access token in memory only.
6. All inventory API calls via Backend with `Authorization: Bearer` header.

### User management (Main Admin)

- **Create user** — assign role, set initial password (temporary; force change on first login optional per product policy).
- **Disable user** — set `status = disabled`; active sessions invalidated on next refresh.
- **Reset password** — Main Admin sets new temporary password; no email notification.
- **Assign role** — one of `main_admin`, `admin`, `salesperson`.
- Prevent disabling the last active Main Admin (`LAST_MAIN_ADMIN` error).

### Security checklist

- [ ] HTTPS enforced in production; internal CA distributed to all clients.
- [ ] `JWT_SECRET_KEY` in environment — never in source control.
- [ ] Passwords never logged, never in audit payload.
- [ ] Generic error message on failed login (no username enumeration).
- [ ] Account lockout after configurable failed attempts.
- [ ] Setup endpoints disabled (409) once `system_initialized = true`.

### Out of scope (Version 1)

- Email delivery
- OTP / MFA
- OAuth, SAML, LDAP, Active Directory
- Self-service password recovery
- Permanent user deletion
- Client-side business data persistence
- Public CA / internet-facing deployment

---

## References

| Document | Path |
|----------|------|
| Project Bible | [docs/PROJECT_BIBLE.md](../docs/PROJECT_BIBLE.md) |
| Product Requirements | [docs/product/PRODUCT_REQUIREMENTS.md](../docs/product/PRODUCT_REQUIREMENTS.md) |
| System Architecture | [docs/SYSTEM_ARCHITECTURE.md](../docs/SYSTEM_ARCHITECTURE.md) |
| Database Design | [docs/database/DATABASE_DESIGN.md](../docs/database/DATABASE_DESIGN.md) |
| API Specification | [docs/api/API_SPECIFICATION.md](../docs/api/API_SPECIFICATION.md) |
| Technology Stack | [docs/TECH_STACK.md](../docs/TECH_STACK.md) |

---

> **Immutability:** This ADR is **Accepted**. Changes to these decisions require a new ADR that supersedes ADR-0010 — do not silently amend accepted decisions in implementation.

*WEBSTUDIO IMS Team — 2026*
