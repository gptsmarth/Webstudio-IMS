import { ASSET_MANIFEST, type IconAssetKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

export class IconRegistry {
  static getIconPath(glyph: IconAssetKey): string {
    if (glyph in ASSET_MANIFEST.icons) {
      return resolvePublicAsset(ASSET_MANIFEST.icons[glyph]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.icons.check);
  }
}
