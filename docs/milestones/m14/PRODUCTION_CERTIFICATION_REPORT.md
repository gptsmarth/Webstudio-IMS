---
Title: Production Certification Report
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14G
Related Documents:
  - docs/milestones/m14/SECURITY_CERTIFICATION.md
  - docs/milestones/m14/PERFORMANCE_CERTIFICATION.md
  - docs/milestones/m14/INFRASTRUCTURE_CERTIFICATION.md
---

# Production Certification Report (M14G)

## Executive Summary

Milestone **14G** performs **production certification** for WEBSTUDIO IMS — validating security controls (authentication, authorization, JWT, RBAC, password policy, Argon2, backup encryption, AI keys, Tally security), performance targets (10,000 inventory, 50,000 sales, 100 concurrent sessions), and infrastructure readiness (HTTPS, LAN deployment, PostgreSQL locality, startup validation).

| Deliverable | Path |
|-------------|------|
| Production Certification Report | This document |
| Security Certification | [SECURITY_CERTIFICATION.md](SECURITY_CERTIFICATION.md) |
| Performance Certification | [PERFORMANCE_CERTIFICATION.md](PERFORMANCE_CERTIFICATION.md) |
| Infrastructure Certification | [INFRASTRUCTURE_CERTIFICATION.md](INFRASTRUCTURE_CERTIFICATION.md) |

**Verdict:** Production certification framework is **implemented and test-covered**. Operators run certification on the commissioned server after M14A–F validation passes.

---

## API surface

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/deployment/production-certification` | Network admin |

**Service:** `production_certification_validation_service.py`  
**Router:** `api/routers/client_deployment.py` (extended — not a new product domain)

### Response structure

```json
{
  "validation_scope": "production_certification",
  "overall_status": "passed | warning | failed",
  "security_certification": { "checks": [...] },
  "performance_certification": { "checks": [...], "targets": {...} },
  "infrastructure_certification": { "checks": [...] },
  "recommendations": [...]
}
```

---

## Security certification summary

| Control | Check key | Status basis |
|---------|-----------|--------------|
| Authentication | `authentication` | Auth router endpoints present |
| Authorization | `authorization` | Permission dependencies |
| JWT | `jwt` | HS256 round-trip; production secret length |
| RBAC | `rbac` | All roles have permissions |
| Password policy | `password_policy` | Min length ≥ 10, history |
| Argon2 | `argon2` | Argon2id hash verification |
| Backup encryption | `backup_encryption` | Extension point; warns if unencrypted in prod |
| AI keys | `ai_keys` | Masking + Fernet for integration keys |
| Tally security | `tally_security` | Read-only XML, no passwords in payload |
| Security headers | `security_headers` | Middleware registered |

Full detail: [SECURITY_CERTIFICATION.md](SECURITY_CERTIFICATION.md)

---

## Performance certification summary

| Target | Check key | Pass criteria |
|--------|-----------|---------------|
| 10,000 inventory | `inventory_10000` | Row count ≥ 10,000 (or index `warning` on empty dev DB) |
| 50,000 sales | `sales_50000` | Row count ≥ 50,000 (or index `warning` on empty dev DB) |
| 100 concurrent sessions | `concurrent_sessions_100` | `refresh_tokens` + pool size guidance |
| Indexes | `indexes_*` | Migrations 0012 + 0027 applied |

Full detail: [PERFORMANCE_CERTIFICATION.md](PERFORMANCE_CERTIFICATION.md)

---

## Infrastructure certification summary

| Requirement | Check key | Pass criteria |
|-------------|-----------|---------------|
| HTTPS readiness | `https_readiness` | TLS files configured or LAN HTTP documented |
| LAN deployment | `lan_deployment` | `API_HOST` accepts LAN (`0.0.0.0`) |
| PostgreSQL locality | `postgresql_locality` | Database on localhost |
| Startup validation | `startup_validation` | Production JWT rules |
| Rate limiting | `rate_limiting` | Optional on private LAN |

Complements M14B: [NETWORK_VALIDATION_REPORT.md](NETWORK_VALIDATION_REPORT.md)

Full detail: [INFRASTRUCTURE_CERTIFICATION.md](INFRASTRUCTURE_CERTIFICATION.md)

---

## Windows operator script

```powershell
cd <install-root>
.\infra\windows\validate-production-certification.ps1 `
  -ApiBaseUrl "http://127.0.0.1:8000" `
  -BearerToken "<network-admin-jwt>"
```

Exit codes: `0` passed, `2` warning, `1` failed.

---

## Test evidence

| Test | Result |
|------|--------|
| `test_production_certification_validation.py` | 3 tests — security, performance, infrastructure check keys |
| `test_performance.py` | Index regression (M9B) |
| `test_auth_security.py` | Login, refresh, sessions |
| `test_permissions.py` | RBAC matrix |

```bash
pytest apps/backend/tests/deployment/test_production_certification_validation.py -q
```

---

## Sign-off checklist

| # | Item | Owner |
|---|------|-------|
| 1 | Certification API returns `overall_status: passed` on production server | WEBSTUDIO engineer |
| 2 | JWT_SECRET rotated (≥ 32 bytes) | Store admin |
| 3 | Inventory ≥ 10,000 rows (or import plan documented) | Store admin |
| 4 | Sales ≥ 50,000 rows (or migration plan documented) | Store admin |
| 5 | LAN + firewall validated (M14B) | IT |
| 6 | Backup ACLs restricted (M14D) | Store admin |
| 7 | Security / Performance / Infrastructure certs reviewed | WEBSTUDIO engineer |

---

## Next milestone

**14G is complete.** Proceed with **14I — Documentation** when ready (14H performance scope merged into 14G certification).
