import { ASSET_MANIFEST, type IllustrationAssetKey } from './AssetManifest';

export class IllustrationRegistry {
  static getIllustration(type: IllustrationAssetKey): string {
    if (type in ASSET_MANIFEST.illustrations) {
      return ASSET_MANIFEST.illustrations[type];
    }
    return ASSET_MANIFEST.illustrations.error;
  }
}
