---
Title: Security Certification
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14G
Related Documents:
  - docs/milestones/m14/PRODUCTION_CERTIFICATION_REPORT.md
  - docs/milestones/m14/PERFORMANCE_CERTIFICATION.md
  - docs/milestones/m14/INFRASTRUCTURE_CERTIFICATION.md
---

# Security Certification (M14G)

## Scope

Production security certification for WEBSTUDIO IMS Version 1.0.0 covers authentication, authorization, JWT, RBAC, password policy, Argon2 hashing, backup encryption posture, AI key handling, and Tally integration security.

**Verdict:** Security controls are **implemented, test-covered, and certifiable** via `GET /api/v1/deployment/production-certification`.

---

## Certification matrix

| Control | Check key | Implementation | Evidence |
|---------|-----------|----------------|----------|
| Authentication | `authentication` | `/api/v1/auth/login`, refresh, logout, sessions | `api/routers/auth.py`, `tests/auth/` |
| Authorization | `authorization` | `require_permission`, `PermissionResolver` | `api/dependencies/auth.py` |
| JWT | `jwt` | HS256, iss/aud, permissions, token_version | `infrastructure/security/jwt.py` |
| RBAC | `rbac` | System roles + custom access roles | `core/permissions.py`, `test_permissions.py` |
| Password policy | `password_policy` | Configurable min length, complexity, history | `password_policy_service.py` |
| Argon2 | `argon2` | Argon2id (time=3, memory=64K, parallelism=4) | `infrastructure/security/password.py` |
| Backup encryption | `backup_encryption` | `BackupEncryptionProvider` extension point | `backup_encryption.py` (NoOp default) |
| AI keys | `ai_keys` | Masked in API; integration keys Fernet-encrypted | `settings_service.py`, `integration_key_service.py` |
| Tally security | `tally_security` | Read-only XML export; GUID dedup | `integrations/tally/xml_client.py` |
| Security headers | `security_headers` | CSP, X-Frame-Options, nosniff | `api/middleware/security_headers.py` |

---

## Authentication & sessions

- **Login:** Username/password with Argon2 verification and account lockout (`default_lockout_threshold`, `default_lockout_duration_minutes`).
- **Refresh tokens:** Rotating refresh tokens stored in `webstudio.refresh_tokens`; revocation on password change and logout-all.
- **Session invalidation:** JWT `token_version` compared to `users.token_version` on every request.
- **Audit:** Failed logins, permission denials, and security events recorded in audit log.

---

## JWT production requirements

| Setting | Requirement |
|---------|-------------|
| `JWT_SECRET` | ≥ 32 bytes in `APP_ENV=production` |
| `JWT_ISSUER` / `JWT_AUDIENCE` | Must match token validation |
| `ACCESS_TOKEN_TTL_MINUTES` | Default 15 minutes |

Startup validation (`core/startup_validation.py`) **blocks** production start with a weak secret.

---

## RBAC

| Role | Scope |
|------|-------|
| `main_admin` | Full system access |
| `admin` | Store administration (no Main Admin exclusives) |
| `salesperson` | Sales and inventory view/transfer |
| Custom access roles | Subset of `ASSIGNABLE_PERMISSIONS` |

See [ROLE_MATRIX_VALIDATION.md](ROLE_MATRIX_VALIDATION.md) for the full matrix.

---

## Password policy (default)

- Minimum **10** characters
- Uppercase, lowercase, and number required
- **5** password history entries (no reuse)
- Symbol optional (configurable via system settings)

---

## Backup encryption

Version 1 ships with **unencrypted** backup archives by default (`NoOpBackupEncryption`). Operators must:

1. Restrict backup folder ACLs to administrators.
2. Store off-site copies on encrypted media.
3. Adopt a future `BackupEncryptionProvider` when encryption-at-rest is mandated.

---

## AI & integration keys

| Key type | Storage | API exposure |
|----------|---------|--------------|
| Gemini / Groq / OpenRouter | `system_settings` (masked in workspace API) | Hint only (`gemini_api_key_hint`) |
| Email / SMS / WhatsApp integration keys | Fernet-encrypted in `integration_api_keys` | Masked hint (`key_hint`) |

**Production recommendation:** Configure AI keys via Settings → Integrations, not only `.env` files.

---

## Tally security

- **Read-only:** IMS sends XML `Export` requests only; no write-back to Tally books.
- **No credentials in XML:** Connection is LAN HTTP to Tally port 9000 on the billing PC.
- **Deduplication:** Processed voucher GUIDs prevent double-import.
- **Network:** Tally port must not be exposed to the public internet.

---

## Operator validation

```http
GET /api/v1/deployment/production-certification
Authorization: Bearer <network-admin-token>
```

Or on Windows Server:

```powershell
.\infra\windows\validate-production-certification.ps1 -BearerToken "<token>"
```

Review `security_certification.checks` in the response and resolve any `failed` or `warning` items before production sign-off.
