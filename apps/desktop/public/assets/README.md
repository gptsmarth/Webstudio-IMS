# WEBSTUDIO IMS Desktop Assets

This directory contains local static assets bundled with the Electron application to ensure 100% offline operation.

## Directories
- `fonts/` — Local typography files (Inter, JetBrains Mono)
- `brand-logos/` — Brand and manufacturer logos (13 bundled brands + default)
- `product-images/` — Seed product photography shipped with the installer
- `placeholders/` — Fallback image assets
- `icons/` — Local vector icons and UI glyphs
- `illustrations/` — Empty state and onboarding illustrations
- `webstudio/` — Application branding (logo, icon, splash)

## Packaging

During `vite build`, everything under `public/assets/` is copied into `dist/assets/` for the renderer (`file://` loads via `resolvePublicAsset()`).

`electron-builder.yml` also copies these folders into installer `extraResources` (same pattern as `webstudio/`):

| Folder | Installer path |
|--------|----------------|
| `brand-logos/` | `resources/assets/brand-logos/` |
| `product-images/` | `resources/assets/product-images/` |
| `webstudio/` | `resources/assets/webstudio/` |

Add new brand SVGs to `brand-logos/` and register them in `src/registries/AssetManifest.ts`.
