/**
 * Resolve paths under `public/assets/` for dev server and packaged Electron (app://).
 * Absolute `/assets/...` URLs break when index.html is loaded via loadFile().
 */
const APP_PROTOCOL = 'app:';

function isPackagedElectronRenderer(): boolean {
  return typeof window !== 'undefined' && window.location.protocol === APP_PROTOCOL;
}

/** Normalize manifest paths like `/assets/brand-logos/dell.svg` → `assets/brand-logos/dell.svg`. */
export function normalizePublicAssetPath(assetPath: string): string {
  return assetPath.replace(/^\/+/, '');
}

/**
 * Resolve paths under `public/assets/` for dev server and packaged Electron (app://).
 */
export function resolvePublicAsset(assetPath: string): string {
  const normalized = normalizePublicAssetPath(assetPath);
  if (isPackagedElectronRenderer()) {
    // Explicit app:// URLs avoid relative resolution quirks in packaged Electron.
    return `app://./${normalized}`;
  }
  const base = import.meta.env.BASE_URL ?? './';
  return `${base}${normalized}`;
}

/** Compare resolved img.src values against manifest-relative asset paths. */
export function assetUrlsEquivalent(currentSrc: string, targetSrc: string): boolean {
  const targetPath = normalizePublicAssetPath(
    targetSrc.replace(/^app:\/\/\.?\/?/, '').replace(/^\.\//, ''),
  );

  try {
    const currentPath = normalizePublicAssetPath(new URL(currentSrc).pathname);
    return currentPath === targetPath || currentPath.endsWith(`/${targetPath}`);
  } catch {
    const currentPath = normalizePublicAssetPath(currentSrc.replace(/^app:\/\/\.?\/?/, ''));
    return currentPath === targetPath || currentPath.endsWith(targetPath);
  }
}
