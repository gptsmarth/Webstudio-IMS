import { ASSET_MANIFEST, type IllustrationAssetKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

export class IllustrationRegistry {
  static getIllustration(type: IllustrationAssetKey): string {
    if (type in ASSET_MANIFEST.illustrations) {
      return resolvePublicAsset(ASSET_MANIFEST.illustrations[type]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.illustrations.error);
  }
}
