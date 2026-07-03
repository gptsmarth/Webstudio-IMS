---
Title: Software Releases Catalog
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Migration: 0037_enterprise_release_catalog
---

# Software Releases Catalog

Enterprise release metadata stored on the WEBSTUDIO Server (M13). Clients read release information from the server API — never directly from GitHub.

## Table: `webstudio.software_releases`

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint | Primary key |
| `release_version` | varchar(32) | Semantic version (e.g. `0.1.0`) |
| `build_number` | integer | Monotonic build counter |
| `release_channel` | `release_channel` enum | `development`, `beta`, `stable` |
| `git_commit` | varchar(64) | Full Git SHA |
| `git_short` | varchar(16) | Short Git SHA |
| `build_timestamp` | timestamptz | Build time (UTC) |
| `release_notes` | text | Markdown release notes |
| `manifest` | jsonb | Full `version-manifest.json` payload |
| `checksums` | jsonb | Artifact name → SHA256 |
| `compatibility_matrix` | jsonb | Min client / DB compatibility |
| `supported_platforms` | jsonb | Platform IDs and artifact names |
| `is_current` | boolean | Active release for channel on this server |
| `published_at` | timestamptz | Publication timestamp |
| `published_by_user_id` | bigint | Approving administrator (future) |

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/releases/current` | Installed / active server release |
| `GET /api/v1/releases/latest` | Newest published release for channel |
| `GET /api/v1/releases/history` | Paginated release history |

## Import

```bash
python3 scripts/release/import-release-catalog.py --catalog-root release --channel stable
```
