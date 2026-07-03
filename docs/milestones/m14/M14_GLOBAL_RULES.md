---
Title: Milestone 14 — Global Rules
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: M14 — Production Deployment & Handover (FINAL)
Related Documents:
  - docs/PROJECT_BIBLE.md
  - docs/milestones/m13/README.md
  - docs/milestones/m12h/DEPLOYMENT_GUIDE.md
  - docs/milestones/m11y/PRODUCTION_DEPLOYMENT_CHECKLIST.md
  - VERSION.json
---

# Milestone 14 — Global Rules

**Milestone 14 is the FINAL milestone of WEBSTUDIO IMS.**

Milestone 14 transforms WEBSTUDIO IMS from a **completed software project** into a **deployed enterprise production system**. Upon successful completion, the project shall be considered **Version 1.0.0 Production Release**.

---

## 1. Scope boundaries (non‑negotiable)

| Rule | Meaning |
|------|---------|
| **No new business features** | Do not add inventory, sales, Tally, reporting, AI, or admin capabilities. |
| **No UI redesign** | Desktop and Flutter layouts, navigation, and workflows are frozen. |
| **No architecture rewrite** | Monorepo structure, service boundaries, and client–server model stay as implemented. |
| **No database redesign** | No new domain tables. Alembic upgrades only if required to apply an already-shipped migration on production. |
| **No API redesign** | Extend OpenAPI only for documenting existing behaviour — no new product endpoints. |
| **Production code only** | All validation uses the already implemented production codebase and packaged artifacts. |

### Allowed work

| Category | Examples |
|----------|----------|
| **Production deployment** | Server install, Windows Service, PostgreSQL, backend start, health checks |
| **Production configuration** | `.env.production`, secrets, CORS, JWT, backup schedule, Tally endpoints |
| **Installer execution** | Server setup EXE, desktop EXE/DMG, mobile APK sideload / App Store prep |
| **System commissioning** | First-time setup wizard, Main Admin, company profile, locations |
| **Production validation** | Smoke tests, end-to-end workflows, backup/restore drill |
| **Device installation** | Desktop and mobile clients on staff devices |
| **Networking validation** | LAN, mDNS discovery, firewall, static IP, client connectivity |
| **Security validation** | TLS, RBAC, lockout, secrets hygiene, audit trail |
| **Performance validation** | Response times, concurrent users, backup duration |
| **Documentation** | Runbooks, handover pack, operator guides (update existing docs) |
| **Production handover** | Sign-off, v1.0.0 version bump, release tag, customer acceptance |

### Forbidden work

- Feature development disguised as “production polish”
- Refactors not required for deployment blockers
- Database wipes in shared environments without explicit operator approval
- Deploying from CI to production without administrator approval (M13 policy)
- Clients contacting GitHub for updates (server remains update authority)

---

## 2. Version target

| Attribute | Value |
|-----------|-------|
| **Release version** | `1.0.0` |
| **Channel** | `stable` |
| **Canonical source** | `VERSION.json` (see M13H) |
| **Completion criterion** | All M14 sub-milestones signed off with reports |

Bump `VERSION.json` to `1.0.0` only in sub-milestone **14J — Production Handover**, after validation passes.

---

## 3. Sub-milestone discipline

Each sub-milestone **must**:

1. Use existing guides and installers (M12/M13) — do not reinvent packaging.
2. Produce a **detailed report** in `docs/milestones/m14/`.
3. **STOP** after the report — no chaining into the next sub-milestone in the same session unless the operator explicitly continues.

| ID | Focus | Report (generated on completion) |
|----|-------|----------------------------------|
| **14A** | Production deployment | `PRODUCTION_DEPLOYMENT_REPORT.md` |
| **14B** | Production configuration | `PRODUCTION_CONFIGURATION_REPORT.md` |
| **14C** | Installer execution & commissioning | `SYSTEM_COMMISSIONING_REPORT.md` |
| **14D** | Production validation (functional) | `PRODUCTION_VALIDATION_REPORT.md` |
| **14E** | Device installation | `DEVICE_INSTALLATION_REPORT.md` |
| **14F** | Networking validation | `NETWORKING_VALIDATION_REPORT.md` |
| **14G** | Security validation | `SECURITY_VALIDATION_REPORT.md` |
| **14H** | Performance validation | `PERFORMANCE_VALIDATION_REPORT.md` |
| **14I** | Documentation | `PRODUCTION_DOCUMENTATION_REPORT.md` |
| **14J** | Production handover & v1.0.0 release | `PRODUCTION_HANDOVER_REPORT.md` |

---

## 4. Entry points (existing — do not duplicate)

| Task | Start here |
|------|------------|
| Server deployment | [m12h/DEPLOYMENT_GUIDE.md](../m12h/DEPLOYMENT_GUIDE.md), [m12b/WINDOWS_SERVICE_GUIDE.md](../m12b/WINDOWS_SERVICE_GUIDE.md) |
| Business-hours operations | [m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md) |
| Installers | [m12c/INSTALLER_GUIDE.md](../m12c/INSTALLER_GUIDE.md) |
| Production env | [m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md](../m12a/PRODUCTION_ENVIRONMENT_CONFIGURATION.md) |
| Pre-deploy checklist | [m11y/PRODUCTION_DEPLOYMENT_CHECKLIST.md](../m11y/PRODUCTION_DEPLOYMENT_CHECKLIST.md) |
| Networking | [m12h/NETWORKING_GUIDE.md](../m12h/NETWORKING_GUIDE.md) |
| Security / backup | [m12h/BACKUP_GUIDE.md](../m12h/BACKUP_GUIDE.md), [m11/SECURITY_QA_REPORT.md](../m11/SECURITY_QA_REPORT.md) |
| Release / updates | [m13/README.md](../m13/README.md) |
| Customer walkthrough | [m12j/CUSTOMER_INSTALLATION_WALKTHROUGH.md](../m12j/CUSTOMER_INSTALLATION_WALKTHROUGH.md) |

---

## 5. Validation principles

- **Evidence over assertion** — reports include commands run, screenshots paths, log excerpts, and pass/fail tables.
- **Production-like environment** — prefer dedicated server hardware or staging that mirrors customer topology.
- **No `fresh-dev.sh` / `docker compose down -v`** on production or shared staging without explicit operator request.
- **Rollback path documented** — every deployment step references M13 rollback and M12 recovery guides.
- **Administrator approval** — deploy and rollback actions require explicit admin sign-off (Deployment Center).

---

## 6. AI agent instructions

When working on Milestone 14:

1. Read this file and [README.md](README.md) before any task.
2. Execute **one sub-milestone** at a time.
3. Do not modify application feature code unless fixing a **production blocker** with minimal diff.
4. Generate the sub-milestone report, update [README.md](README.md) status, then **STOP**.

---

## 7. Exit criteria (M14 complete)

Milestone 14 is complete when:

- [ ] All sub-milestones **14A–14J** have Final reports
- [ ] `VERSION.json` is `1.0.0` / `stable` with production git metadata
- [ ] Server, desktop, and mobile clients run against production configuration
- [ ] Networking, security, and performance validations pass
- [ ] Production handover pack delivered to operator
- [ ] `PROJECT_BIBLE.md` Current Release updated to **1.0.0 Production Release**

**After Milestone 14: feature development requires a new product version charter — M14 is closed.**
