import { ASSET_MANIFEST, type PlaceholderAssetKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

export class ProductPlaceholderRegistry {
  static getPlaceholder(category: PlaceholderAssetKey = 'generic'): string {
    if (category in ASSET_MANIFEST.placeholders) {
      return resolvePublicAsset(ASSET_MANIFEST.placeholders[category]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.placeholders.generic);
  }
}
