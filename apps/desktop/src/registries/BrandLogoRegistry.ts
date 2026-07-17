import { ASSET_MANIFEST, BUNDLED_BRAND_LOGO_KEYS, type BundledBrandLogoKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

const KNOWN_BRAND_KEYS = new Set<BundledBrandLogoKey>(BUNDLED_BRAND_LOGO_KEYS);

export class BrandLogoRegistry {
  /** All bundled brand logo keys shipped with the desktop app (excludes default). */
  static listBundledBrandKeys(): BundledBrandLogoKey[] {
    return [...BUNDLED_BRAND_LOGO_KEYS];
  }

  /** Normalize catalogue / inventory brand names to bundled asset keys. */
  static normalizeBrandKey(brandName: string): BundledBrandLogoKey | 'default' {
    const trimmed = brandName.trim().toLowerCase();
    if (KNOWN_BRAND_KEYS.has(trimmed as BundledBrandLogoKey)) {
      return trimmed as BundledBrandLogoKey;
    }

    const firstToken = trimmed.split(/[\s\-_/]+/).find((part) => part.length > 0);
    if (firstToken && KNOWN_BRAND_KEYS.has(firstToken as BundledBrandLogoKey)) {
      return firstToken as BundledBrandLogoKey;
    }

    for (const key of KNOWN_BRAND_KEYS) {
      if (trimmed.includes(key)) {
        return key;
      }
    }

    return 'default';
  }

  /** Suggest a bundled logo filename from a brand display name (e.g. "Asus" → "asus.svg"). */
  static logoFilenameForBrand(brandName: string): string | null {
    const normalized = BrandLogoRegistry.normalizeBrandKey(brandName);
    if (normalized !== 'default') {
      return `${normalized}.svg`;
    }
    return null;
  }

  /**
   * True when logo_filename points at a server-managed, user-uploaded logo
   * (written by the backend as `/assets/brand-logos/brand-{id}.{ext}`) rather
   * than a bundled asset. Uploaded logos are fetched through the authenticated
   * image proxy; bundled ones resolve to local assets.
   */
  static isUploadedLogo(logoFilename?: string | null): boolean {
    const trimmed = logoFilename?.trim();
    return Boolean(trimmed && trimmed.startsWith('/assets/brand-logos/brand-'));
  }

  /** Prefer explicit logo_filename; otherwise match bundled assets by brand name. */
  static resolveLogoFilename(brandName: string, logoFilename?: string | null): string | null {
    const trimmed = logoFilename?.trim();
    if (trimmed) {
      return trimmed.split('/').pop() ?? trimmed;
    }
    return BrandLogoRegistry.logoFilenameForBrand(brandName);
  }

  static getLogo(brandName: string): string {
    const normalized = BrandLogoRegistry.normalizeBrandKey(brandName);
    if (normalized !== 'default') {
      return resolvePublicAsset(ASSET_MANIFEST.brandLogos[normalized]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.brandLogos.default);
  }

  static getFallbackLogo(brandName: string): string {
    const normalized = BrandLogoRegistry.normalizeBrandKey(brandName);
    if (normalized !== 'default' && normalized in ASSET_MANIFEST.brandLogosPng) {
      return resolvePublicAsset(ASSET_MANIFEST.brandLogosPng[normalized]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.brandLogosPng.default);
  }
}
