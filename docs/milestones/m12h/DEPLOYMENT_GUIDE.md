---
Title: Deployment Guide — WEBSTUDIO IMS Production
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
Related: DEPLOY-001
---

# Deployment Guide

Production rollout for a retail showroom. **Authoritative detail:** [DEPLOY-001](../../deployment/DEPLOYMENT_GUIDE.md).

---

## 1. Deployment phases

| Phase | Duration | Activities |
|-------|----------|------------|
| **Plan** | 1–2 days | Hardware, network, IP plan, backup target |
| **Install** | 1 day | Server, DB, migrations, service |
| **Configure** | 0.5 day | Setup wizard, office deployment, Tally |
| **Pilot** | 2–3 days | Admin + 2 users; verify sync and sales |
| **Train** | 1 day | Employee guide walkthrough |
| **Go-live** | 1 day | Full staff; monitor sync health |

---

## 2. Pre-deployment checklist

- [ ] Server PC delivered (Windows 11 Pro, UPS)
- [ ] PostgreSQL 16 installed or bundled with server setup
- [ ] Release artifacts verified (checksums)
- [ ] LAN cabling / Wi‑Fi coverage confirmed
- [ ] Tally ERP 9 XML port 9000 enabled on billing PC
- [ ] Main Admin identified
- [ ] Off-site backup destination agreed

---

## 3. Server deployment

1. Run **WEBSTUDIO Server Setup.exe**
2. Confirm `D:\WEBSTUDIO-IMS` data layout
3. Verify service: `sc query "WEBSTUDIO Server"`
4. Apply migrations (installer runs automatically)
5. Configure `.env` from `config/env/.env.production` template

**Business hours:** See [M12B Business Hours Guide](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md)

---

## 4. Client deployment

| Client | Method |
|--------|--------|
| Admin desktop | Setup.exe first |
| Floor desktops | Setup.exe + saved server URL |
| Android | APK sideload or MDM |
| iOS | TestFlight when available |

---

## 5. Integration deployment

| Integration | Guide |
|-------------|-------|
| Tally | [Tally Guide](TALLY_GUIDE.md) + [M12E](../m12e/TALLY_DEPLOYMENT_GUIDE.md) |
| AI | [AI Guide](AI_GUIDE.md) |
| Excel export | Settings → Excel path |

---

## 6. Validation sign-off

| Role | Sign-off item |
|------|---------------|
| IT | Network wizard all green |
| Admin | Backup + restore test |
| Manager | Sample sale from Tally → inventory SOLD |
| Engineering | `version-manifest.json` archived |

---

## 7. Rollback plan

If go-live fails:

1. Stop WEBSTUDIO Server service
2. Restore PostgreSQL from pre-go-live backup
3. Reinstall previous release artifacts
4. Document incident in maintenance log

See [M12A Rollback Strategy](../m12a/ROLLBACK_STRATEGY.md)

---

## 8. Post-go-live

- Daily: check Tally Sync Health
- Weekly: verify backup timestamp
- Monthly: off-site backup copy
- Quarterly: restore drill

[Maintenance Guide](MAINTENANCE_GUIDE.md)
