---
Title: Tally Troubleshooting
Version: 1.0.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Related Documents: docs/milestones/m12/TALLY_CONNECTIVITY_HARDENING_REPORT.md
---

# Tally Troubleshooting

## Host / IP configuration

Use **Host / IP address** in Settings → Tally (not a fixed IP unless you use DHCP reservations):

| Format | Example |
|--------|---------|
| IPv4 | `192.168.1.25` |
| Hostname | `LENOVO-TALLY` |
| mDNS | `LENOVO-TALLY.local` |

Prefer a **hostname** so the Tally laptop can roam between office Wi‑Fi networks without reconfiguration.

## Connection test stages

Use **Test connection** in Tally settings. Each stage is reported separately:

1. **Host Resolution** — DNS/mDNS lookup (always at runtime; never cached permanently)
2. **TCP Connection** — port reachability (default 9000)
3. **XML Server** — Tally Prime XML response

## Common messages

| Message | Action |
|---------|--------|
| Tally workstation is currently offline. | Power on laptop; ensure Tally Prime is running |
| Unable to connect to the configured Tally workstation. | Check firewall; verify server and laptop on same LAN |
| The configured host could not be resolved. | Fix hostname/DNS; try `.local` or register DNS A record |
| Tally XML Server not enabled. | In Tally: enable XML Server on configured port |
| Waiting for the Tally workstation to become available. | Normal when laptop is off; IMS continues working |

## WEBSTUDIO still works when Tally is offline

Inventory, sales, reports, users, settings, AI, backups, mobile, and desktop are unaffected. Only Tally sync is unavailable until the workstation returns.

## Health endpoint

Administrators and monitoring tools can use:

`GET /api/v1/integrations/tally/health`

See [TALLY_CONNECTIVITY_HARDENING_REPORT.md](../../milestones/m12/TALLY_CONNECTIVITY_HARDENING_REPORT.md) for deployment guidance.
