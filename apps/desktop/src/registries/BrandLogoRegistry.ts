import { ASSET_MANIFEST, type BrandLogoKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

export class BrandLogoRegistry {
  static getLogo(brandName: string): string {
    const normalized = brandName.trim().toLowerCase() as BrandLogoKey;
    if (normalized in ASSET_MANIFEST.brandLogos) {
      return resolvePublicAsset(ASSET_MANIFEST.brandLogos[normalized]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.brandLogos.default);
  }

  static getFallbackLogo(brandName: string): string {
    const normalized = brandName.trim().toLowerCase() as BrandLogoKey;
    if (normalized in ASSET_MANIFEST.brandLogosPng) {
      return resolvePublicAsset(ASSET_MANIFEST.brandLogosPng[normalized]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.brandLogosPng.default);
  }
}
