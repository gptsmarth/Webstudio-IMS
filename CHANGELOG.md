---
Title: Changelog
Version: 0.1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: None
---

# Changelog

All notable changes to WEBSTUDIO IMS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.2] - 2026-07-04

### Fixed

- **Tally Prime sync:** use **Day Book** XML export instead of legacy `Vouchers` collection (fixes 0 invoices imported on Tally Prime)
- **Tally company name:** document and support full Tally Prime company names (e.g. `WEBSTUDIO - (from 1-Apr-…)`)
- **Windows NSSM:** registry-backed `AppEnvironmentExtra` apply; skip empty env vars; default `-EnvFile` path; avoid `DATABASE_URL=` override crash
- **Schedulers:** read `WEBSTUDIO_*_SCHEDULER` from Settings `.env` via `get_settings()` (fixes “Manual sync only” banner when NSSM incomplete)
- **Backup:** `POSTGRES_BIN` resolution for Windows service (`pg_dump` on PATH)
- **Deployment Center:** clearer check/download messages when no newer GitHub release exists
- **Gemini AI:** default model `gemini-2.5-flash-lite`; improved error messages
- **Android:** manual server URL entry; barcode scanner error handling
- **Tally sync history:** display start/end times in **local timezone** (was UTC)

### Changed

- Tally production validation expects Day Book export template

## [1.0.1] - 2026-07-03

### Fixed

- Initial production shop deployment fixes (server installer, finalize scripts)

## [1.0.0] - 2026-07-02

### Added

- **M12 Production release** — desktop, mobile, and Windows server installers
- Enterprise Tally deployment (M12E): GUID incremental sync, hidden metadata, operator guides
- Office deployment wizard (M12F): auto-detect, IP recommendation, deployment summary
- Business-hours Windows server deployment (M12B): scheduler persistence, graceful shutdown
- Multi-SSID networking and Tally connectivity probe (M12D)
- Release bundle: `version-manifest.json`, `checksums.sha256`, migration scripts, environment profiles
- Production and crash logging (`WEBSTUDIO_LOG_DIR`, `WEBSTUDIO_CRASH_LOG_DIR`, Electron crashReporter)

### Changed

- Sales API omits internal Tally GUID/MasterID from client responses

## [0.1.0-mvp] - 2026-06-27

### Added

- Repository architecture and folder hierarchy
- Documentation templates and placeholder files
- AI collaboration context files
- ADR and specification templates
