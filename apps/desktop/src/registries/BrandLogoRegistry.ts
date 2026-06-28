import { ASSET_MANIFEST, type BrandLogoKey } from './AssetManifest';

export class BrandLogoRegistry {
  static getLogo(brandName: string): string {
    const normalized = brandName.trim().toLowerCase() as BrandLogoKey;
    if (normalized in ASSET_MANIFEST.brandLogos) {
      return ASSET_MANIFEST.brandLogos[normalized];
    }
    return ASSET_MANIFEST.brandLogos.default;
  }

  static getFallbackLogo(brandName: string): string {
    const normalized = brandName.trim().toLowerCase() as BrandLogoKey;
    if (normalized in ASSET_MANIFEST.brandLogosPng) {
      return ASSET_MANIFEST.brandLogosPng[normalized];
    }
    return ASSET_MANIFEST.brandLogosPng.default;
  }
}
