---
Title: Infrastructure Certification
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14G
Related Documents:
  - docs/milestones/m14/PRODUCTION_CERTIFICATION_REPORT.md
  - docs/milestones/m14/NETWORK_VALIDATION_REPORT.md
  - docs/milestones/m14/INFRASTRUCTURE_CHECKLIST.md
---

# Infrastructure Certification (M14G)

## Scope

Infrastructure certification confirms the dedicated Windows server deployment is ready for production LAN operation: HTTPS readiness, LAN binding, co-located PostgreSQL, startup validation, and optional rate limiting.

**Verdict:** Infrastructure controls are **implemented and certifiable** alongside M14B networking validation.

---

## Certification matrix

| Requirement | Check key | Implementation |
|-------------|-----------|----------------|
| HTTPS readiness | `https_readiness` | `TLS_CERT_PATH`, `TLS_KEY_PATH` settings |
| LAN deployment | `lan_deployment` | `API_HOST=0.0.0.0`, mDNS, discovery candidates |
| PostgreSQL locality | `postgresql_locality` | `DATABASE_URL` on localhost |
| Startup validation | `startup_validation` | Production JWT secret gate |
| Rate limiting | `rate_limiting` | `RATE_LIMIT_ENABLED` (optional on private LAN) |

---

## HTTPS readiness

| Mode | Configuration |
|------|---------------|
| **LAN HTTP (V1 default)** | Clients use `http://<server-ip>:8000` on trusted store network |
| **HTTPS (recommended when available)** | Set `TLS_CERT_PATH` and `TLS_KEY_PATH`; terminate TLS on server or reverse proxy |

Certification reports `warning` when TLS files are absent in production — acceptable for private LAN V1 deployments per [SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md).

---

## LAN deployment

| Setting | Production value |
|---------|------------------|
| `API_HOST` | `0.0.0.0` (accept LAN clients) |
| `API_PORT` | `8000` (default) |
| `MDNS_ENABLED` | `true` (client discovery) |
| `WEBSTUDIO_DISCOVERY_CANDIDATES` | Server static IP or hostname |

Complement with M14B networking validation:

```http
GET /api/v1/network/admin/report?scope=production
```

See [NETWORK_VALIDATION_REPORT.md](NETWORK_VALIDATION_REPORT.md) and [FIREWALL_CONFIGURATION_GUIDE.md](FIREWALL_CONFIGURATION_GUIDE.md).

---

## PostgreSQL

- Database runs **on the same machine** as the WEBSTUDIO Server Windows Service.
- Port **5432** bound to localhost only (not exposed to LAN).
- Alembic head applied before certification (`alembic upgrade head`).

---

## Startup validation

Production (`APP_ENV=production`) enforces:

- `JWT_SECRET` length ≥ 32 bytes
- Server refuses to start with `change-me-in-production`

Configure via `.env.production` during M14A commissioning.

---

## Windows Server checklist

| Step | Action |
|------|--------|
| 1 | WEBSTUDIO Server service running |
| 2 | PostgreSQL service running |
| 3 | Firewall rule for TCP 8000 (LAN subnet) |
| 4 | Static IP or DHCP reservation documented |
| 5 | Backup folder writable |
| 6 | Run certification script |

```powershell
.\infra\windows\validate-production-certification.ps1 -BearerToken "<main-admin-token>"
.\infra\windows\validate-production-network.ps1 -BearerToken "<token>"
```

---

## Operator validation

```http
GET /api/v1/deployment/production-certification
Authorization: Bearer <network-admin-token>
```

Resolve `infrastructure_certification.checks` with status `failed` before production handover.
