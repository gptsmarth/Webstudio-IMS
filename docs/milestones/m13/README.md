---
Title: Milestone 13 — Enterprise Release Management
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 13 — Enterprise Release Management

Implements the server-side **Release Management subsystem** and **GitHub Release Synchronization**. Extends M12 release engineering; does not redesign desktop or mobile UI.

## Deliverables

| Milestone | Report |
|-----------|--------|
| 13A — Release Management | [ENTERPRISE_RELEASE_MANAGEMENT_REPORT.md](ENTERPRISE_RELEASE_MANAGEMENT_REPORT.md) |
| 13B — GitHub Sync | [GITHUB_RELEASE_SYNCHRONIZATION_REPORT.md](GITHUB_RELEASE_SYNCHRONIZATION_REPORT.md) |
| 13C — Deployment Center | [DEPLOYMENT_CENTER_REPORT.md](DEPLOYMENT_CENTER_REPORT.md) |
| 13D — Deployment Engine | [DEPLOYMENT_ENGINE_REPORT.md](DEPLOYMENT_ENGINE_REPORT.md) |
| 13E — Client Update Platform | [CLIENT_UPDATE_PLATFORM_REPORT.md](CLIENT_UPDATE_PLATFORM_REPORT.md) |
| 13F — Rollback Platform | [ROLLBACK_PLATFORM_REPORT.md](ROLLBACK_PLATFORM_REPORT.md) |
| 13G — Enterprise GitHub Actions | [CICD_PIPELINE_REPORT.md](CICD_PIPELINE_REPORT.md) |
| 13H — Version Management | [ENTERPRISE_VERSION_MANAGEMENT_REPORT.md](ENTERPRISE_VERSION_MANAGEMENT_REPORT.md) |
| 13I — Deployment Monitoring | [DEPLOYMENT_ANALYTICS_REPORT.md](DEPLOYMENT_ANALYTICS_REPORT.md) |

| Item | Path |
|------|------|
| Database schema (releases) | [docs/database/software-releases.md](../../database/software-releases.md) |
| Database schema (GitHub sync) | [docs/database/github-release-sync.md](../../database/github-release-sync.md) |
| Database schema (deployment engine) | [docs/database/deployment-engine.md](../../database/deployment-engine.md) |
| Database schema (enterprise rollback) | [docs/database/enterprise-rollback.md](../../database/enterprise-rollback.md) |
| OpenAPI fragment | [docs/api/openapi/releases-v1.yaml](../../api/openapi/releases-v1.yaml) |

## API (public read)

| Method | Endpoint |
|--------|----------|
| GET | `/api/v1/releases/current` |
| GET | `/api/v1/releases/latest` |
| GET | `/api/v1/releases/history` |

## Operations

```bash
# Import bundles from release/ into PostgreSQL catalog
python3 scripts/release/import-release-catalog.py --channel stable

# Regenerate manifest (schema 2.0.0 with channels + build numbers)
python3 scripts/release/lib/generate_manifest.py
```

**Rule:** Desktop and mobile clients consume release metadata from WEBSTUDIO Server only. GitHub is the release repository; the server is the update authority.
