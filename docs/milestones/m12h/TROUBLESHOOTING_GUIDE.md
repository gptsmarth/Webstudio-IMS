---
Title: Troubleshooting Guide — WEBSTUDIO IMS
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 12H
---

# Troubleshooting Guide

Symptom-based resolution for production showrooms.

---

## 1. Quick diagnostics

| Check | Command / UI |
|-------|--------------|
| Server alive | `curl http://server:8000/health/live` |
| DB ready | `curl http://server:8000/health/ready` |
| Client connection | Desktop toolbar status |
| Tally | Settings → Test Connection |
| Network | Recovery Center → Network wizard |

---

## 2. Connection issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Desktop **Offline** | Server off or Wi‑Fi | Power server; same SSID/VLAN |
| Server not in list | mDNS blocked | Manual URL `http://IP:8000` |
| Intermittent disconnect | Wi‑Fi weak | Wired LAN for server; AP placement |
| Works on one PC only | Wrong URL saved | Clear config; rediscover |

See [Networking Guide](NETWORKING_GUIDE.md)

---

## 3. Login issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Invalid credentials | Wrong password | Admin reset |
| System not initialized | Setup incomplete | Complete setup wizard |
| Account locked | Failed attempts | Wait lockout period |
| Token expired | Idle timeout | Log in again |

---

## 4. Tally sync issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Sync Health Offline | Tally PC off | Start Tally |
| Zero imports | Wrong company name | Fix Settings → Tally |
| Serial not imported | Not in inventory | Receive item first |
| High skipped count | Normal after re-sync | GUID dedup working |

[Tally Guide](TALLY_GUIDE.md) · [M12E Recovery](../m12e/RECOVERY_GUIDE.md)

---

## 5. Inventory issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Serial not found | Typo or not received | Search variants; add item |
| Cannot mark sold | Already sold | Check sales history |
| Wrong location | Transfer not done | Inventory → change location |

---

## 6. Backup / restore issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Backup failed | Disk full | Free space on data root |
| Restore checksum error | Corrupt file | Use older backup |
| Count mismatch | Partial restore | Full restore retry |

[Backup Guide](BACKUP_GUIDE.md) · [Restore Guide](RESTORE_GUIDE.md)

---

## 7. Performance issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow search | Large inventory | Expected; use filters |
| Slow sync | Large Tally window | Normal after long weekend |
| API timeout | Server load | Restart service; check PostgreSQL |

---

## 8. Server service issues

```powershell
sc query "WEBSTUDIO Server"
Get-Content D:\WEBSTUDIO-IMS\logs\webstudio-api.log -Tail 50
```

| Log message | Action |
|-------------|--------|
| PostgreSQL connection refused | Start PostgreSQL service |
| JWT_SECRET too short | Fix `.env` in production |
| Migration failed | Run `alembic upgrade head` manually |

[Server Guide](SERVER_GUIDE.md)

---

## 9. Mobile issues

| Symptom | Fix |
|---------|-----|
| Update required | Install latest APK/IPA |
| iOS local network | Enable permission in iOS Settings |
| Android install blocked | Allow unknown sources |

[Android Guide](ANDROID_GUIDE.md) · [iOS Guide](IOS_GUIDE.md)

---

## 10. Escalation to engineering

Include:

1. `version-manifest.json` version
2. Symptom and time
3. Server log excerpt (no secrets)
4. Steps to reproduce
5. Screenshot of Sync Health / Recovery Center

---

## 11. Related guides

- [M12D Network Troubleshooting](../m12d/TROUBLESHOOTING_GUIDE.md)
- [Tally ERP troubleshooting](../../integrations/tally-erp9/troubleshooting.md)
