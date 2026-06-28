import { ProductPlaceholderRegistry } from '../../registries/ProductPlaceholderRegistry';

const CACHE_PREFIX = 'webstudio.product-image.';
const REMOTE_FETCH_ENABLED = true;

export type ProductImageSource = 'cached' | 'placeholder' | 'remote' | 'none';

export interface ProductImageResult {
  src: string;
  source: ProductImageSource;
  canUpload: boolean;
}

/**
 * Product image resolution with local cache first, HTTPS product URL, then placeholder.
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

    const remoteUrl = options?.remoteUrl?.trim();
    if (remoteUrl?.startsWith('https://')) {
      const loadable = await this.canLoadImage(remoteUrl);
      if (loadable) {
        return { src: remoteUrl, source: 'remote', canUpload: true };
      }
    }

    if (REMOTE_FETCH_ENABLED) {
      const remote = await this.fetchRemoteImage(productModelId, {
        brandName: options?.brandName,
        modelName: options?.modelName,
        remoteUrl,
      });
      if (remote) {
        return { src: remote, source: 'remote', canUpload: true };
      }
    }

    return {
      src: ProductPlaceholderRegistry.getPlaceholder(category),
      source: 'placeholder',
      canUpload: true,
    };
  }

  static canLoadImage(url: string): Promise<boolean> {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(true);
      img.onerror = () => resolve(false);
      img.referrerPolicy = 'no-referrer';
      img.src = url;
    });
  }

  /** Try stored HTTPS URL again (validated) when no cache exists. */
  static async fetchRemoteImage(
    _productModelId: string,
    options?: { brandName?: string | null; modelName?: string | null; remoteUrl?: string | null },
  ): Promise<string | null> {
    const remoteUrl = options?.remoteUrl?.trim();
    if (remoteUrl?.startsWith('https://') && await this.canLoadImage(remoteUrl)) {
      return remoteUrl;
    }
    return null;
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
