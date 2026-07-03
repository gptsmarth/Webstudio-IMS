---
Title: Maintenance Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Maintenance Guide

Ongoing maintenance for production WEBSTUDIO IMS deployments.

---

## 1. Maintenance schedule

| Task | Frequency | Owner |
|------|-----------|-------|
| Verify backup succeeded | Daily | Admin |
| Review Tally sync health | Daily | Admin |
| Off-site backup copy | Weekly | IT |
| Disk space check | Weekly | IT |
| User access review | Monthly | Admin |
| Restore drill | Quarterly | IT + Admin |
| Password policy review | Quarterly | Admin |
| Software upgrade | Per release | IT |

---

## 2. Daily (business hours)

- [ ] Server PC powered on before staff arrive
- [ ] Tally PC on with company loaded
- [ ] Desktop toolbar shows **Connected**
- [ ] Tally Sync Health **Healthy** (or expected Offline if Tally not used yet)

Evening: graceful shutdown per [M12B Business Hours](../m12b/BUSINESS_HOURS_DEPLOYMENT_GUIDE.md)

---

## 3. Software upgrades

### Server

1. Read `RELEASE_NOTES.md` in release bundle
2. Manual backup
3. Stop WEBSTUDIO Server service
4. Run installer or replace files
5. `alembic upgrade head`
6. Start service; verify `/health/ready`
7. Upgrade clients to matching version

### Clients

Distribute new Setup.exe / APK after server upgrade.

[M12A Upgrade Strategy](../m12a/UPGRADE_STRATEGY.md)

---

## 4. Database maintenance

| Task | Command / tool |
|------|----------------|
| Vacuum | PostgreSQL autovacuum (monitor) |
| Migration | Alembic only — no manual DDL |
| Audit retention | Scheduler purges per policy |

---

## 5. Log rotation

- Server: `WEBSTUDIO_LOG_DIR` — 10 MB × 5 files (automatic)
- NSSM stdout rotation configured in service install
- Desktop: manual archive of `webstudio-client.log` if large

`config/logging/logrotate-webstudio.conf.example`

---

## 6. Certificate renewal (HTTPS)

If using internal CA TLS:

1. Generate new cert before expiry
2. Update `TLS_CERT_PATH` / `TLS_KEY_PATH`
3. Restart service
4. Update desktop saved URLs if hostname changes

DEPLOY-001 § Certificate Renewal

---

## 7. Scheduler maintenance

Schedulers persist state in `scheduler_runtime_state`. After long outages:

- No manual intervention — startup restores `next_run_at`
- Office Deployment Wizard re-run if paths changed

---

## 8. Deprecation and EOL

- `min_client_version` on server blocks old clients
- Announce upgrades 1 week before forcing minimum version
- Archive release bundles for 2 years minimum

---

## 9. Maintenance windows

| Window | Activities |
|--------|------------|
| After close | Server upgrade, restore drill |
| Sunday (if closed) | PostgreSQL minor updates |
| Never during | Peak sales hours without admin present |

---

## 10. Records

Maintain log:

| Date | Action | Version | Operator |
|------|--------|---------|----------|
| | | | |

Store with deployment summary JSON from Office Deployment Wizard.
