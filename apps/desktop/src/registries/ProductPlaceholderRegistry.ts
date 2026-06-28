import { ASSET_MANIFEST, type PlaceholderAssetKey } from './AssetManifest';

export class ProductPlaceholderRegistry {
  static getPlaceholder(category: PlaceholderAssetKey = 'generic'): string {
    if (category in ASSET_MANIFEST.placeholders) {
      return ASSET_MANIFEST.placeholders[category];
    }
    return ASSET_MANIFEST.placeholders.generic;
  }
}
