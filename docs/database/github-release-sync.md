---
Title: GitHub Release Synchronization
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Migration: 0038_github_release_sync
---

# GitHub Release Synchronization

Server-side GitHub Releases polling and artifact download queue (M13B). Only the WEBSTUDIO Server contacts GitHub; clients never do.

## Tables

### `webstudio.release_download_jobs`

| Column | Description |
|--------|-------------|
| `github_release_id` | GitHub release ID |
| `tag_name` | Git tag (e.g. `v0.1.0`) |
| `release_version` | Normalized semver |
| `build_number` | Parsed build counter |
| `release_channel` | Target channel |
| `status` | `pending`, `queued`, `downloading`, `verifying`, `completed`, `failed`, `skipped` |
| `bundle_dir` | Local storage path (default `D:\WEBSTUDIO-IMS\Updates\vX.Y.Z` on Windows) |
| `manifest_validated` | Manifest schema validation passed |
| `checksums_verified` | SHA256 verification passed |
| `attempt_count` / `max_attempts` | Retry queue control |
| `next_retry_at` | Scheduled retry timestamp |

### `webstudio.release_download_artifacts`

Per-asset download state with `partial_path` for resumable downloads and `bytes_downloaded` for recovery.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `WEBSTUDIO_GITHUB_REPO` | — | `owner/repo` |
| `WEBSTUDIO_GITHUB_TOKEN` | — | PAT for private repos / rate limits |
| `WEBSTUDIO_RELEASE_SYNC_INTERVAL_SECONDS` | `900` (15 min) | Polling interval |
| `WEBSTUDIO_RELEASE_UPDATES_ROOT` | `D:\WEBSTUDIO-IMS\Updates` (Windows) | Download root |
| `WEBSTUDIO_RELEASE_SYNC_SCHEDULER` | `1` | Enable background loop |
| `github_release_sync_enabled` (setting) | `false` | Operator toggle |
| `github_release_repo` (setting) | — | Repo override when env unset |

**Rule:** Downloads never auto-deploy. Administrator approval is required before activation.

## API (admin)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/releases/sync/status` | Polling state and queue counts |
| `GET /api/v1/releases/sync/history` | Completed downloads |
| `GET /api/v1/releases/sync/failures` | Failed / skipped downloads |
