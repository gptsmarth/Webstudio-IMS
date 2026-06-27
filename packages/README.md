---
Title: Shared Packages — README
Version: 0.1.0
Status: Draft
Owner: WEBSTUDIO IMS Team
Last Updated: 2026-06-27
Related Documents: docs/README.md
---

# Shared Packages

## Purpose

Shared libraries consumed by multiple applications in the WEBSTUDIO IMS monorepo.

## Expected Files

- shared-kernel/ — Domain types and validation
- api-client/ — Typed API client
- auth/ — Authentication and authorization
- ui-components/ — Shared UI components
- integrations/ — Tally and Excel connectors
- testing/ — Shared test utilities

## Audience

All developers

## Guidelines

Packages must not depend on apps/. Apps may depend on packages. No application code until development phase begins.
