# Brand Logos Registry Directory

This folder contains manufacturer and brand logos bundled locally for offline display across the WEBSTUDIO IMS desktop application.

## Expected Filenames & Conventions
All filenames MUST be strictly **lowercase**. The application queries logos through the `BrandLogoRegistry` using these normalized names.

### Supported Brands List:
- `asus.svg` / `asus.png`
- `acer.svg` / `acer.png`
- `hp.svg` / `hp.png`
- `dell.svg` / `dell.png`
- `lenovo.svg` / `lenovo.png`
- `msi.svg` / `msi.png`
- `apple.svg` / `apple.png`
- `sandisk.svg` / `sandisk.png`
- `logitech.svg` / `logitech.png`
- `tp-link.svg` / `tp-link.png`
- `canon.svg` / `canon.png`
- `epson.svg` / `epson.png`
- `brother.svg` / `brother.png`
- `default.svg` / `default.png` (Fallback logo for unknown brands)

## Format Guidelines
1. **SVG Preference**: Always use vector `.svg` whenever available for crisp rendering across Retina displays and arbitrary scaling.
2. **PNG Fallback**: If vector graphics are unavailable, provide transparent `.png` files with identical base naming (minimum resolution 256x256px).
