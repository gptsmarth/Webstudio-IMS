---
Title: API Documentation — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
Related: API-001
---

# API Documentation

Production index for the WEBSTUDIO IMS REST API. **Full contract:** [API-001](../../api/API_SPECIFICATION.md).

---

## 1. Base URLs

| Environment | Base URL |
|-------------|----------|
| Production (LAN) | `http://{server-host}:8000/api/v1` |
| Production (TLS) | `https://{server-host}:8443/api/v1` |
| Development | `http://localhost:8000/api/v1` |

OpenAPI YAML: [docs/api/openapi/webstudio-ims-api-v1.yaml](../../api/openapi/webstudio-ims-api-v1.yaml)

---

## 2. Authentication

| Method | Header |
|--------|--------|
| Bearer JWT | `Authorization: Bearer {access_token}` |

Obtain tokens via `POST /api/v1/auth/login`. Refresh via `POST /api/v1/auth/refresh`.

---

## 3. Response envelope

```json
{
  "success": true,
  "data": { },
  "error": null,
  "meta": {
    "correlation_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

Errors include `code`, `message`, `details`.

---

## 4. Core endpoint groups

| Group | Prefix | Purpose |
|-------|--------|---------|
| Health | `/health/*` | Liveness, readiness (no auth) |
| Setup | `/api/v1/setup/*` | First-time init (unauthenticated when uninitialized) |
| Discovery | `/api/v1/discovery/*` | LAN client health (public metadata) |
| Auth | `/api/v1/auth/*` | Login, logout, session |
| Inventory | `/api/v1/inventory/*` | CRUD, search, transfer |
| Sales | `/api/v1/sales/*` | Sales workspace |
| Dashboard | `/api/v1/dashboard/*` | KPIs |
| Tally | `/api/v1/integrations/tally/*` | Sync, dashboard, health |
| Settings | `/api/v1/settings/*` | Workspace settings |
| Backup | `/api/v1/settings/backups` | Backup run |
| Reports | `/api/v1/reports/*` | JSON + export |
| Deployment | `/api/v1/deployment/office/*` | Office wizard (M12F) |
| Network | `/api/v1/network/admin/*` | Network validation |

---

## 5. Version headers

Clients should send:

```
X-Client-Version: 0.1.0
X-Client-Platform: desktop | mobile
```

Server enforces `min_client_version` on protected routes.

---

## 6. Permissions

RBAC via permission strings, e.g.:

- `inventory:read`, `inventory:create`
- `settings:modify`
- `tally:run_sync`
- `backup:manage`

See API-001 § RBAC matrix.

---

## 7. Rate limiting

Production: `RATE_LIMIT_ENABLED=true` (default 100 req/min per IP when enabled).

---

## 8. Tally API privacy

Public Tally endpoints **never** return GUID, MasterID, or AlterID. Operational fields only.

---

## 9. Tools

| Tool | Use |
|------|-----|
| FastAPI `/docs` | Dev/staging Swagger UI |
| `packages/api-client` | TypeScript client |
| Postman | Import OpenAPI YAML |

---

## 10. Change process

API changes require:

1. Update API-001 and OpenAPI YAML
2. ADR if architectural
3. Version bump per [VERSION_STRATEGY](../m12a/VERSION_STRATEGY.md)
