import { ASSET_MANIFEST, type IconAssetKey } from './AssetManifest';

export class IconRegistry {
  static getIconPath(glyph: IconAssetKey): string {
    if (glyph in ASSET_MANIFEST.icons) {
      return ASSET_MANIFEST.icons[glyph];
    }
    return ASSET_MANIFEST.icons.check;
  }
}
