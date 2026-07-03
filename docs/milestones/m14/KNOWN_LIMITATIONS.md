---
Title: Known Limitations
Version: 1.0.0
Status: Final
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-07-02
Milestone: 14J
---

# Known Limitations — WEBSTUDIO IMS v1.0.0

Documented constraints at production release. Not defects — design boundaries for Version 1.

---

## Platform

| Limitation | Detail |
|------------|--------|
| Server OS | Windows 11 Pro dedicated PC only — no Linux/macOS server in V1 |
| Cloud deployment | Not supported — on-premise LAN only |
| HTTPS | Optional on LAN; HTTP default for private store networks |
| Multi-store | Single server per showroom deployment |

---

## Integrations

| Limitation | Detail |
|------------|--------|
| Tally | Read-only import — no write-back to Tally books |
| Tally versions | ERP 9 XML port 9000 — not Tally Prime cloud |
| Excel | Export sync only — no bidirectional Excel import |
| Barcode (desktop) | Keyboard-wedge scanners only — no proprietary SDK |
| Barcode (mobile) | Camera scan — requires device permission |

---

## Security & data

| Limitation | Detail |
|------------|--------|
| Backup encryption | Archives unencrypted by default — rely on filesystem ACLs |
| AI keys | Stored in database settings (masked in API) — not HSM |
| Offline mobile | Limited cache — writes require live server |
| Concurrent scale | Certified to 100 sessions with pool tuning — not load-balanced multi-server |

---

## Release & updates

| Limitation | Detail |
|------------|--------|
| GitHub sync | Optional — requires `WEBSTUDIO_GITHUB_REPO` configuration |
| iOS distribution | Requires TestFlight or enterprise signing — not App Store V1 |
| Client updates | Server-authoritative — no peer-to-peer updates |

---

## Search & performance

| Limitation | Detail |
|------------|--------|
| Free-text search | `ILIKE` without trigram — acceptable at V1 scale with indexes |
| Performance evidence | Index certification on dev; full 10k/50k load test on commissioned server |

---

## UI & features

| Limitation | Detail |
|------------|--------|
| Mobile settings | Read-only integration keys list — create/rotate on desktop |
| Custom reports | Predefined report types — no ad-hoc report builder |
| Multi-language UI | English primary — locale settings for formats only |

---

## Workarounds

| Limitation | Workaround |
|------------|------------|
| mDNS blocked | Manual server URL in clients |
| No backup encryption | Off-site encrypted USB + ACLs |
| No AI key | Manual spec entry on Add laptop |
| Tally offline | Manual mark-as-sold (admin) until sync resumes |

See [FUTURE_ROADMAP.md](FUTURE_ROADMAP.md) for planned improvements.
