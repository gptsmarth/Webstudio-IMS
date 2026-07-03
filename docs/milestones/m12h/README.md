---
Title: Milestone 12H — Production Documentation
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
---

# Milestone 12H — Production Documentation

Complete operator and engineering documentation for WEBSTUDIO IMS production deployment.

## Audience index

| Audience | Start here |
|----------|------------|
| **Showroom owner / Main Admin** | [Administrator Guide](ADMINISTRATOR_GUIDE.md) |
| **Sales staff / floor employees** | [Employee Guide](EMPLOYEE_GUIDE.md) |
| **IT installer** | [Installation Guide](INSTALLATION_GUIDE.md) → [Deployment Guide](DEPLOYMENT_GUIDE.md) |
| **Network technician** | [Networking Guide](NETWORKING_GUIDE.md) |
| **Server operator** | [Server Guide](SERVER_GUIDE.md) |
| **Software engineer** | [Developer Guide](DEVELOPER_GUIDE.md) → [API Documentation](API_DOCUMENTATION.md) |

## Complete documentation set

### Operations

| Document | Description |
|----------|-------------|
| [Administrator Guide](ADMINISTRATOR_GUIDE.md) | Users, roles, settings, Tally, backups, reports |
| [Employee Guide](EMPLOYEE_GUIDE.md) | Daily tasks: inventory, sales, search, notifications |
| [Installation Guide](INSTALLATION_GUIDE.md) | Install server, desktop, mobile from release artifacts |
| [Deployment Guide](DEPLOYMENT_GUIDE.md) | End-to-end production rollout |
| [Server Guide](SERVER_GUIDE.md) | Windows service, PostgreSQL, schedulers, logs |
| [Networking Guide](NETWORKING_GUIDE.md) | LAN, SSID, firewall, discovery, static IP |
| [Desktop Guide](DESKTOP_GUIDE.md) | Windows/macOS client |
| [Android Guide](ANDROID_GUIDE.md) | APK install and daily use |
| [iOS Guide](IOS_GUIDE.md) | IPA sideload / TestFlight (when signed) |

### Data protection

| Document | Description |
|----------|-------------|
| [Backup Guide](BACKUP_GUIDE.md) | Manual and scheduled backups |
| [Restore Guide](RESTORE_GUIDE.md) | Restore from archive |
| [Recovery Guide](RECOVERY_GUIDE.md) | Disaster recovery and business-hours outages |

### Integrations

| Document | Description |
|----------|-------------|
| [Tally Guide](TALLY_GUIDE.md) | Tally ERP 9 sync for operators |
| [AI Guide](AI_GUIDE.md) | Gemini / AI enrichment settings |

### Engineering

| Document | Description |
|----------|-------------|
| [API Documentation](API_DOCUMENTATION.md) | REST API index and conventions |
| [Developer Guide](DEVELOPER_GUIDE.md) | Repo, build, test, extend |
| [Maintenance Guide](MAINTENANCE_GUIDE.md) | Upgrades, patches, housekeeping |
| [Troubleshooting Guide](TROUBLESHOOTING_GUIDE.md) | Symptom → resolution |

### Diagrams

| Document | Description |
|----------|-------------|
| [Architecture Diagrams](diagrams/ARCHITECTURE_DIAGRAMS.md) | System components and data flow |
| [Deployment Diagrams](diagrams/DEPLOYMENT_DIAGRAMS.md) | Physical and logical deployment |
| [Networking Diagrams](diagrams/NETWORKING_DIAGRAMS.md) | LAN topology and discovery |

## Milestone 12 documentation map

| Milestone | Focus |
|-----------|-------|
| [M12A](../m12a/) | Packaging audit |
| [M12B](../m12b/) | Business-hours Windows server |
| [M12C](../m12c/) | Installer packaging |
| [M12D](../m12d/) | Enterprise networking |
| [M12E](../m12e/) | Tally deployment |
| [M12F](../m12f/) | Office deployment wizard |
| [M12G](../m12g/) | Release engineering |
| **M12H** | **This documentation pack** |

## Canonical references (authority)

| ID | Document |
|----|----------|
| DEPLOY-001 | [docs/deployment/DEPLOYMENT_GUIDE.md](../../deployment/DEPLOYMENT_GUIDE.md) |
| ARCH-001 | [docs/SYSTEM_ARCHITECTURE.md](../../SYSTEM_ARCHITECTURE.md) |
| API-001 | [docs/api/API_SPECIFICATION.md](../../api/API_SPECIFICATION.md) |
| M12 milestones | [m12a](../m12a/) … [m12g](../m12g/) |

## Document control

- **Version:** 1.0.0 (aligned with release `0.1.0`)
- **Next review:** After each production release tag
- **Feedback:** Main Admin → IT → engineering via issue tracker
