---
Title: Contributing Guide
Version: 0.1.0
Status: Active
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: None
---

# Contributing to WEBSTUDIO IMS

## Overview

Thank you for contributing to WEBSTUDIO IMS. This document outlines the contribution process for all team members.

## Getting Started

1. Read [docs/development/getting-started/local-setup.md](docs/development/getting-started/local-setup.md)
2. Review [docs/development/conventions/git-workflow.md](docs/development/conventions/git-workflow.md)
3. Familiarize yourself with relevant ADRs in [adr/records/](adr/records/)

## Branch Naming

| Prefix | Usage |
|--------|-------|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes |
| `chore/` | Tooling, dependencies |
| `release/` | Release preparation |

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `infra`

## Pull Request Requirements

- [ ] Linked issue or spec ID
- [ ] Tests added or updated (when applicable)
- [ ] Documentation updated
- [ ] ADR created (for architectural changes)
- [ ] No secrets or credentials committed

## Code Review

- Minimum one approval required
- Two approvals for changes to `apps/backend/`, `database/`, `infra/`

## Questions

Contact the WEBSTUDIO IMS Team.
