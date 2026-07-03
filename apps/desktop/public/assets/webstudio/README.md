# WEBSTUDIO IMS Core Branding Assets

This directory stores the official identity assets for WEBSTUDIO IMS. The desktop application automatically consumes these files for window icons, header branding, splash screens, and installer packaging without requiring code restructuring.

## Asset Specification & Requirements

| Filename | Purpose | Recommended Dimensions | Preferred Format |
| :--- | :--- | :--- | :--- |
| `logo.svg` | Primary universal brand logo | Arbitrary (Vector 4:1 ratio) | SVG (Scalable Vector Graphics) |
| `logo-dark.svg` | Dark ink logo for light UI surfaces (sidebar, headers) | Arbitrary (Vector 4:1 ratio) | SVG with dark/slate lettering |
| `logo-light.svg` | Light ink logo for dark UI surfaces | Arbitrary (Vector 4:1 ratio) | SVG with light/white lettering |
| `icon.svg` | Universal vector app icon | 512x512px canvas | SVG |
| `icon.ico` | Windows desktop application & taskbar icon | Multi-resolution (16px to 256px) | ICO (Windows Icon) |
| `icon.icns` | macOS dock & bundle app icon | Multi-resolution (16px to 1024px)| ICNS (Apple Icon Image) |
| `icon.png` | High-res fallback icon for Linux / web notifications | 1024x1024px | PNG (Transparent background) |

**Important:** `icon.ico`, `icon.icns`, and `icon.png` must be real binary raster files — not SVG renamed with another extension. CI runs `scripts/release/validate-branding-icons.sh` before packaging.

Regenerate all platform icons from the canonical **`icon.png`** master (1024×1024):

```bash
bash scripts/release/regenerate-branding-icons.sh
```

Replace the master from a new design file:

```bash
bash scripts/release/regenerate-branding-icons.sh --source /path/to/new-icon.png
```

Re-render `icon.png` from `icon.svg` instead (vector source):

```bash
bash scripts/release/regenerate-branding-icons.sh --from-svg
```

This updates `icon.ico`, `icon.icns`, and syncs `icon.png` to Flutter.
| `splash.svg` | App boot splash screen artwork | 800x600px canvas | SVG |
| `favicon.svg` | Web browser tab icon (for web dev builds) | 64x64px canvas | SVG |

## Consumption Rule
Never reference external CDN branding. All components and packaging scripts must point directly to this registry folder.
