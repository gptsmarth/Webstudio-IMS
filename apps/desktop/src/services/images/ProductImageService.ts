import { ProductPlaceholderRegistry } from '../../registries/ProductPlaceholderRegistry';
import { resolvePublicAsset } from '../../utils/resolvePublicAsset';
import { ProductSpecService } from '../api/ProductSpecService';

const CACHE_PREFIX = 'webstudio.product-image.';
const LOCAL_UPLOAD_CACHE_SUFFIX = '__local__';

export type ProductImageSource = 'cached' | 'placeholder' | 'remote' | 'none';

export interface ProductImageResult {
  src: string;
  source: ProductImageSource;
  canUpload: boolean;
}

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

/**
 * Product image resolution: local cache → backend proxy (CORS-safe) → auto-resolve from web.
 */
export class ProductImageService {
  static cacheKey(productModelId: string, remoteUrl?: string | null): string {
    const normalizedUrl = remoteUrl?.trim() || LOCAL_UPLOAD_CACHE_SUFFIX;
    return `${CACHE_PREFIX}${productModelId}|${normalizedUrl}`;
  }

  static getCachedDataUrl(productModelId: string, remoteUrl?: string | null): string | null {
    try {
      const cached = localStorage.getItem(this.cacheKey(productModelId, remoteUrl));
      // Older scrapers cached 8×8 tracking pixels as data URLs (~1–2 KB).
      if (cached && cached.length < 4096 && remoteUrl?.startsWith('/assets/product-images/')) {
        localStorage.removeItem(this.cacheKey(productModelId, remoteUrl));
        return null;
      }
      return cached;
    } catch {
      return null;
    }
  }

  static setCachedDataUrl(
    productModelId: string,
    dataUrl: string,
    remoteUrl?: string | null,
  ): void {
    try {
      localStorage.setItem(this.cacheKey(productModelId, remoteUrl), dataUrl);
    } catch {
      // Ignore quota errors — UI falls back to placeholder.
    }
  }

  static clearCached(productModelId: string, remoteUrl?: string | null): void {
    try {
      localStorage.removeItem(this.cacheKey(productModelId, remoteUrl));
    } catch {
      // no-op
    }
  }

  static clearCachedForModel(productModelId: string): void {
    try {
      const prefix = `${CACHE_PREFIX}${productModelId}|`;
      const keysToRemove: string[] = [];
      for (let index = 0; index < localStorage.length; index += 1) {
        const key = localStorage.key(index);
        if (key?.startsWith(prefix)) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((key) => localStorage.removeItem(key));
    } catch {
      // no-op
    }
  }

  static getPlaceholderSrc(category: 'laptop' | 'generic' = 'laptop'): string {
    return ProductPlaceholderRegistry.getPlaceholder(category);
  }

  static async resolve(
    productModelId: string,
    options?: {
      remoteUrl?: string | null;
      category?: 'laptop' | 'generic';
      brandName?: string | null;
      modelName?: string | null;
    },
  ): Promise<ProductImageResult> {
    const category = options?.category ?? 'laptop';
    const remoteUrl = options?.remoteUrl?.trim() || null;

    if (remoteUrl) {
      const cached = this.getCachedDataUrl(productModelId, remoteUrl);
      if (cached) {
        return { src: cached, source: 'cached', canUpload: true };
      }
    } else {
      const uploaded = this.getCachedDataUrl(productModelId, LOCAL_UPLOAD_CACHE_SUFFIX);
      if (uploaded) {
        return { src: uploaded, source: 'cached', canUpload: true };
      }
    }

    if (remoteUrl?.startsWith('/assets/')) {
      // Packaged desktop builds may ship stale product-images that shadow the
      // live server (and defeat self-heal). Always prefer the authenticated
      // proxy for managed product photos; keep bundled lookup for logos only.
      const isManagedProductImage = remoteUrl.startsWith('/assets/product-images/');
      if (!isManagedProductImage) {
        const bundledSrc = resolvePublicAsset(remoteUrl);
        if (await this.tryDirectImage(bundledSrc)) {
          return { src: bundledSrc, source: 'remote', canUpload: true };
        }
      }
      const proxied = await this.loadViaBackendProxy(productModelId, remoteUrl);
      if (proxied) {
        return proxied;
      }
      // Proxy 404 often means the server is self-healing — drop any stale
      // cached junk for this URL so the next resolve can pick up the rewrite.
      this.clearCached(productModelId, remoteUrl);
      return {
        src: ProductPlaceholderRegistry.getPlaceholder(category),
        source: 'placeholder',
        canUpload: true,
      };
    }

    let resolvedRemoteUrl = remoteUrl;
    if (!resolvedRemoteUrl?.startsWith('https://') && !resolvedRemoteUrl?.startsWith('/assets/')) {
      try {
        const resolved = await ProductSpecService.resolveModelImage(productModelId);
        // Backend may return source=pending while discovery runs in the background.
        resolvedRemoteUrl = resolved.product_image_url?.trim() || null;
        if (!resolvedRemoteUrl && resolved.source === 'pending') {
          return {
            src: ProductPlaceholderRegistry.getPlaceholder(category),
            source: 'placeholder',
            canUpload: true,
          };
        }
      } catch {
        resolvedRemoteUrl = null;
      }
    }

    if (resolvedRemoteUrl?.startsWith('https://')) {
      const cached = this.getCachedDataUrl(productModelId, resolvedRemoteUrl);
      if (cached) {
        return { src: cached, source: 'cached', canUpload: true };
      }

      const proxied = await this.loadViaBackendProxy(productModelId, resolvedRemoteUrl);
      if (proxied) {
        return proxied;
      }

      const direct = await this.tryDirectImage(resolvedRemoteUrl);
      if (direct) {
        return { src: resolvedRemoteUrl, source: 'remote', canUpload: true };
      }
    }

    return {
      src: ProductPlaceholderRegistry.getPlaceholder(category),
      source: 'placeholder',
      canUpload: true,
    };
  }

  static async loadViaBackendProxy(
    productModelId: string,
    remoteUrl: string,
  ): Promise<ProductImageResult | null> {
    try {
      const blob = await ProductSpecService.fetchImageBlob(remoteUrl);
      if (!blob.type.startsWith('image/')) {
        this.clearCached(productModelId, remoteUrl);
        return null;
      }
      // Reject obviously corrupt/tiny payloads that older scrapers cached.
      if (blob.size > 0 && blob.size < 2048) {
        this.clearCached(productModelId, remoteUrl);
        return null;
      }
      const dataUrl = await blobToDataUrl(blob);
      this.setCachedDataUrl(productModelId, dataUrl, remoteUrl);
      return { src: dataUrl, source: 'remote', canUpload: true };
    } catch {
      this.clearCached(productModelId, remoteUrl);
      return null;
    }
  }

  static tryDirectImage(url: string): Promise<boolean> {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.referrerPolicy = 'no-referrer';
      img.src = url;
    });
  }

  static canLoadImage(url: string): Promise<boolean> {
    return this.tryDirectImage(url);
  }

  static async uploadFromFile(productModelId: string, file: File): Promise<ProductImageResult> {
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
    this.clearCachedForModel(productModelId);
    this.setCachedDataUrl(productModelId, dataUrl, LOCAL_UPLOAD_CACHE_SUFFIX);
    return { src: dataUrl, source: 'cached', canUpload: true };
  }
}
