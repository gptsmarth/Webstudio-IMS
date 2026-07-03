---
Title: Milestone 12F — Office Deployment Wizard
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 12F — Office Deployment Wizard

First-run **Office Deployment Wizard** for showroom administrators. No manual `.env` or config file editing is required for standard deployment.

## Deliverables

| Area | Location |
|------|----------|
| Detection engine | `services/office_deployment_service.py` |
| REST API | `POST/GET /api/v1/deployment/office/*` |
| Desktop wizard | `components/settings/OfficeDeploymentWizard.tsx` |
| Auto-prompt on login | `layouts/AppShell.tsx` (when deployment not completed) |
| Manual re-run | Settings → Backup → Recovery Center → **Office deployment** |

## Detected components

| Check | Description |
|-------|-------------|
| Network | LAN IP, hostname, mDNS state |
| PostgreSQL | Connection + schema revision |
| Windows Service | `WEBSTUDIO Server` service (Windows production) |
| API | Local port listening |
| Backup Path | Writable backup directory |
| Image Storage | Product image storage path |
| AI Provider | Provider keys and enrichment config |
| Tally | Connectivity when enabled |
| Firewall | Advisory + `configure-firewall.ps1` guidance |
| Ports | API, PostgreSQL, mDNS, Tally |

## IP recommendation

The wizard recommends **DHCP Reservation** when mDNS is active, otherwise **Static IP** (with the alternative documented). Administrators configure the router or server adapter — WEBSTUDIO saves application paths and client URLs automatically.

## Saved automatically

- `backup_folder` → `{data_root}/backups`
- `product_image_storage_path` → `{data_root}/assets/product-images`
- `office_server_url` → detected LAN API URL
- `office_discovery_urls` → JSON list for client discovery health
- `office_deployment_summary` → full deployment summary JSON
- `office_deployment_completed` → `true`

## API reference

```
GET  /api/v1/deployment/office/status
POST /api/v1/deployment/office/detect
POST /api/v1/deployment/office/apply
POST /api/v1/deployment/office/complete
GET  /api/v1/deployment/office/summary
```

Requires `settings:view` or `dashboard:system_status`.

## Related milestones

- **12B** — Windows service and business-hours deployment
- **12D** — Network validation (subset reused)
- **12E** — Tally deployment (configured after wizard or in Settings)
