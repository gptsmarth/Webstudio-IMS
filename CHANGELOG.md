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

## [1.7.6] - 2026-07-16

### Added

- **Delete serial:** remove a single unsold inventory unit from live stock (desktop + mobile); available count updates immediately; sales history unchanged
- **Add inventory:** “Apply first location to all” and “Apply first purchase price to all” on desktop and mobile add wizards
- **Mobile add:** per-unit purchase price field
- **CI:** Server Release workflow — backend quality + server installer only (no desktop/mobile rebuild)

### Changed

- **Delete product model:** cascades deletion of inventory serials for that model while preserving sale snapshots forever
- Migration `0050`: notifications and Tally line inventory FKs use `ON DELETE SET NULL`

### Fixed

- Product image scraper hard-blocks `/books/` paths on manufacturer CDNs (CI quality gate)

## [1.7.5] - 2026-07-16

### Fixed

- **Mobile add inventory:** create-or-find product model on 409 so serials still save (no orphan zero-stock models)
- **Mobile:** colour field capped at 64 chars; clearer API error messages in add wizards
- **Mobile sync:** silent background polls (no repeating “Syncing…” banner); narrower inventory refresh
- **Sales GST:** Tally lines with tax breakdown store inclusive amount in `sale_amount` and taxable in `sale_amount_excluding_gst`
- **Product images:** broken placeholder fallback on desktop; intermittent mobile image loading (cache + retry)

### Changed

- **Spec auto-fetch:** Gemini-only path stays fast — no image scraping during configuration lookup (saves tokens)
- **Images:** background discovery + periodic backfill for models missing images (free web scrape, no AI tokens)
- **Image search:** deterministic queries instead of extra AI calls for image-query generation

## [1.0.3] - 2026-07-05

### Added

- **Accessory inventory:** category, part number, accessory type; Add Accessory wizard on desktop and mobile
- **Stock / inventory filters:** All products, Laptops only, Accessories only
- **Mobile:** Add Accessory flow, category-aware stock cards, part-number search, accessory spec auto-fetch
- **Tally:** accessory part-number matching, multi-serial line expansion, mixed laptop + accessory invoices
- **Docs:** ground-floor server + first-floor Tally layout (same shop LAN)

### Fixed

- **Tally sync:** GST on all sale lines; serial match authoritative; case-insensitive serial/model matching
- **Accessory auto-fetch:** Gemini lookup import fix; faster image/spec fetch with dedup
- **Mobile barcode:** scan arm delay, part-number field routing, keyboard/serial scan fixes
- **Inventory models:** nullable laptop fields for accessory API responses (mobile)

### Changed

- Mobile Add button opens laptop or accessory chooser; server URL still `http://192.168.29.100:8000`

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
