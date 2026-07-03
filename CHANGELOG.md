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

### Added

- Milestone 12G release engineering: version manifest, checksums, env profiles, migration packaging

## [0.1.0] - 2026-07-02

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
