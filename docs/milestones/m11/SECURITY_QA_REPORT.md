---
Title: Milestone 11 — Security QA Report
Version: 1.0.0
Status: Complete
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m11/KNOWN_ISSUES_REPORT.md
---

# Security QA Report

## Authentication & session security

| Control | Status | Evidence |
|---------|--------|----------|
| Invalid JWT rejected | ✅ | Auth middleware tests |
| Expired JWT → 401 | ✅ | Client refresh flow |
| Refresh token rotation | ✅ | Reuse revokes token family |
| Token version invalidation on password change | ✅ | `authentication_service.change_password` |
| Account lockout | ✅ | `test_auth_security.py` |
| Permission denied audit | ✅ | Logs path + required permission |
| Argon2 password hashing | ✅ | `argon2-cffi` |
| Password history (5) | ✅ | Migration 0020 |

| Gap | ID | Severity |
|-----|-----|----------|
| Session timeout setting not server-enforced | BACK-006 | Medium |

## Authorization (RBAC)

| Test | Result |
|------|--------|
| Inventory hardening matrix (all roles) | ✅ |
| Reference data 401/403 | ✅ |
| Reports, dashboard, Tally auth | ✅ |
| Desktop audit export permission | ❌ DESK-001 |
| Desktop Tally vs settings permission | ⚠️ DESK-004 |

## Injection & input validation

| Vector | Status | Notes |
|--------|--------|-------|
| SQL injection | ✅ Pattern review | ORM + bound parameters; no fuzz tests (TEST-001) |
| Path traversal (assets) | ✅ | `resolve()` + root check on managed assets |
| File upload (images) | ⚠️ | Content-Type only on upload (SEC-001) |
| Backup import | ⚠️ | No size limit (SEC-002) |

## Desktop Electron security

| Setting | Value |
|---------|-------|
| contextIsolation | true |
| nodeIntegration | false |
| sandbox | true |
| Preload | contextBridge IPC only |

**Minor:** IPC config/storage keys not validated (Low).

## Flutter mobile security

| Control | Status |
|---------|--------|
| Tokens in flutter_secure_storage | ✅ |
| Android encryptedSharedPreferences | ✅ |
| iOS Keychain first_unlock | ✅ |
| Profile in Hive (non-secret) | ✅ Acceptable |
| LAN-only ATS exception | ✅ Documented |

## Secrets & API keys

- Integration keys stored encrypted in DB
- Gemini/Tally config in system_settings (backed up in manifest)
- JWT secret must be ≥32 bytes in production (test env uses shorter key — warning only)

## Security headers

- `X-Content-Type-Options: nosniff` via middleware ✅

## Recommended pre-production actions

1. Fix DESK-001 (audit export RBAC)
2. Add magic-byte validation on image upload (SEC-001)
3. Set production `JWT_SECRET` ≥ 32 bytes
4. Add SQL injection fuzz tests for search endpoints (TEST-001)
5. Cap backup import upload size (SEC-002)

## Verdict

Security posture is **strong for a LAN-deployed IMS**. Address Medium gaps before internet-facing deployment.
