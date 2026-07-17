import { ProductSpecService } from '../api/ProductSpecService';

const CACHE_PREFIX = 'webstudio.brand-logo.';

/** In-memory cache so a logo used across many rows is fetched once per session. */
const memoryCache = new Map<string, string>();
const inFlight = new Map<string, Promise<string | null>>();

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

/**
 * Resolves a server-uploaded brand logo (`/assets/brand-logos/...`) to a data
 * URL by fetching it through the authenticated image proxy. Results are cached
 * in memory and localStorage so the `<img>` can render offline afterwards.
 */
export class BrandLogoService {
  static getCached(logoUrl: string): string | null {
    const mem = memoryCache.get(logoUrl);
    if (mem) return mem;
    try {
      const stored = localStorage.getItem(CACHE_PREFIX + logoUrl);
      if (stored) {
        memoryCache.set(logoUrl, stored);
        return stored;
      }
    } catch {
      // ignore storage errors — will refetch
    }
    return null;
  }

  static async resolve(logoUrl: string): Promise<string | null> {
    const cached = this.getCached(logoUrl);
    if (cached) return cached;

    const existing = inFlight.get(logoUrl);
    if (existing) return existing;

    const task = (async () => {
      try {
        const blob = await ProductSpecService.fetchImageBlob(logoUrl);
        if (!blob.type.startsWith('image/')) return null;
        const dataUrl = await blobToDataUrl(blob);
        memoryCache.set(logoUrl, dataUrl);
        try {
          localStorage.setItem(CACHE_PREFIX + logoUrl, dataUrl);
        } catch {
          // quota — memory cache still serves this session
        }
        return dataUrl;
      } catch {
        return null;
      } finally {
        inFlight.delete(logoUrl);
      }
    })();
    inFlight.set(logoUrl, task);
    return task;
  }

  static clear(logoUrl: string): void {
    memoryCache.delete(logoUrl);
    try {
      localStorage.removeItem(CACHE_PREFIX + logoUrl);
    } catch {
      // no-op
    }
  }
}
