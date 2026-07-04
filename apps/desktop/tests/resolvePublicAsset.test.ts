import { describe, expect, it } from 'vitest';
import { extractAppRelativePath } from '../electron/app-asset-path';
import {
  assetUrlsEquivalent,
  normalizePublicAssetPath,
  resolvePublicAsset,
} from '../src/utils/resolvePublicAsset';

describe('resolvePublicAsset', () => {
  it('normalizes leading slashes', () => {
    expect(normalizePublicAssetPath('/assets/brand-logos/dell.svg')).toBe(
      'assets/brand-logos/dell.svg',
    );
  });

  it('resolves relative paths for dev builds', () => {
    expect(resolvePublicAsset('/assets/webstudio/logo.svg')).toContain('assets/webstudio/logo.svg');
  });

  it('resolves explicit app:// paths in packaged renderer', () => {
    const originalWindow = globalThis.window;
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: { location: { protocol: 'app:' } },
    });
    try {
      expect(resolvePublicAsset('/assets/brand-logos/asus.svg')).toBe(
        'app://./assets/brand-logos/asus.svg',
      );
      expect(resolvePublicAsset('assets/webstudio/logo-light.svg')).toBe(
        'app://./assets/webstudio/logo-light.svg',
      );
    } finally {
      Object.defineProperty(globalThis, 'window', {
        configurable: true,
        value: originalWindow,
      });
    }
  });

  it('compares resolved asset URLs by pathname', () => {
    expect(
      assetUrlsEquivalent(
        'app://./assets/brand-logos/default.svg',
        './assets/brand-logos/default.svg',
      ),
    ).toBe(true);
    expect(
      assetUrlsEquivalent('app://./assets/brand-logos/dell.svg', './assets/brand-logos/hp.svg'),
    ).toBe(false);
  });
});

describe('extractAppRelativePath', () => {
  it('maps app:// logo requests to dist/assets paths', () => {
    expect(extractAppRelativePath('app://./assets/brand-logos/dell.svg')).toBe(
      'assets/brand-logos/dell.svg',
    );
    expect(extractAppRelativePath('app://./assets/webstudio/logo.svg')).toBe(
      'assets/webstudio/logo.svg',
    );
  });

  it('defaults empty paths to index.html', () => {
    expect(extractAppRelativePath('app://./index.html')).toBe('index.html');
    expect(extractAppRelativePath('app://./')).toBe('index.html');
  });
});
