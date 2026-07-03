import { ASSET_MANIFEST, type WebstudioAssetKey } from './AssetManifest';
import { resolvePublicAsset } from '../utils/resolvePublicAsset';

export class WebstudioAssetRegistry {
  static getAsset(key: WebstudioAssetKey): string {
    if (key in ASSET_MANIFEST.webstudio) {
      return resolvePublicAsset(ASSET_MANIFEST.webstudio[key]);
    }
    return resolvePublicAsset(ASSET_MANIFEST.webstudio.logo);
  }

  /**
   * Pick logo with contrast against the current UI theme.
   * Assets are named by ink color: `logo-dark` = dark lettering, `logo-light` = light lettering.
   */
  static getLogoForTheme(theme: 'light' | 'dark'): string {
    return theme === 'dark'
      ? resolvePublicAsset(ASSET_MANIFEST.webstudio.logoLight)
      : resolvePublicAsset(ASSET_MANIFEST.webstudio.logoDark);
  }
}
