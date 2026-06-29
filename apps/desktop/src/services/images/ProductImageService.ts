import { ProductPlaceholderRegistry } from '../../registries/ProductPlaceholderRegistry';
import { ProductSpecService } from '../api/ProductSpecService';

const CACHE_PREFIX = 'webstudio.product-image.';

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
  static cacheKey(productModelId: string): string {
    return `${CACHE_PREFIX}${productModelId}`;
  }

  static getCachedDataUrl(productModelId: string): string | null {
    try {
      return localStorage.getItem(this.cacheKey(productModelId));
    } catch {
      return null;
    }
  }

  static setCachedDataUrl(productModelId: string, dataUrl: string): void {
    try {
      localStorage.setItem(this.cacheKey(productModelId), dataUrl);
    } catch {
      // Ignore quota errors — UI falls back to placeholder.
    }
  }

  static clearCached(productModelId: string): void {
    try {
      localStorage.removeItem(this.cacheKey(productModelId));
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
    const cached = this.getCachedDataUrl(productModelId);
    if (cached) {
      return { src: cached, source: 'cached', canUpload: true };
    }

    let remoteUrl = options?.remoteUrl?.trim() || null;
    if (remoteUrl?.startsWith('/assets/')) {
      return { src: remoteUrl, source: 'remote', canUpload: true };
    }
    if (!remoteUrl?.startsWith('https://')) {
      try {
        const resolved = await ProductSpecService.resolveModelImage(productModelId);
        remoteUrl = resolved.product_image_url?.trim() || null;
      } catch {
        remoteUrl = null;
      }
    }

    if (remoteUrl?.startsWith('https://')) {
      const proxied = await this.loadViaBackendProxy(productModelId, remoteUrl);
      if (proxied) {
        return proxied;
      }

      const direct = await this.tryDirectImage(remoteUrl);
      if (direct) {
        return { src: remoteUrl, source: 'remote', canUpload: true };
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
        return null;
      }
      const dataUrl = await blobToDataUrl(blob);
      this.setCachedDataUrl(productModelId, dataUrl);
      return { src: dataUrl, source: 'remote', canUpload: true };
    } catch {
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
    this.setCachedDataUrl(productModelId, dataUrl);
    return { src: dataUrl, source: 'cached', canUpload: true };
  }
}
