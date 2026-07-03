/**
 * Resolve paths under `public/assets/` for dev server and packaged Electron (file://).
 * Absolute `/assets/...` URLs break when index.html is loaded via loadFile().
 */
export function resolvePublicAsset(assetPath: string): string {
  const normalized = assetPath.startsWith('/') ? assetPath.slice(1) : assetPath;
  const base = import.meta.env.BASE_URL ?? './';
  return `${base}${normalized}`;
}
