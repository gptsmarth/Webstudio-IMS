---
Title: Security Policy
Version: 0.1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: None
---

# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Development |

## Reporting a Vulnerability

**Do not** open public issues for security vulnerabilities.

Report security issues to the WEBSTUDIO IMS Team through designated private channels.

Include:

- Description of the vulnerability
- Steps to reproduce
- Affected components and versions
- Potential impact

## Response Timeline

| Stage | Target |
|-------|--------|
| Acknowledgment | 48 hours |
| Initial assessment | 5 business days |
| Resolution plan | 10 business days |

## Security Guidelines

- Never commit secrets, API keys, or credentials
- Use environment variables via `config/env/.env.example` templates
- Follow [docs/security/README.md](docs/security/README.md)
