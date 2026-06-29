import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import type { StorageType, StorageUnit } from './InventoryService';

export interface ProductSpecLookupResult {
  model_name: string;
  cpu: string;
  gpu: string | null;
  ram_gb: number;
  storage_value: string;
  storage_unit: StorageUnit;
  storage_type: StorageType;
  display: string | null;
  color_options: string | null;
  product_image_url: string | null;
  description: string | null;
  notes: string | null;
  source: string;
}

export interface ProductImageResolveResult {
  product_image_url: string | null;
  source: string;
}

export class ProductSpecService {
  static async lookupSpec(input: {
    model_number: string;
    model_name?: string;
    brand_name?: string;
  }): Promise<ProductSpecLookupResult | null> {
    LoggingService.info('API', 'Looking up product spec via Gemini', { model: input.model_number });
    const client = await ApiClientProvider.getClient();
    try {
      return await client.post<ProductSpecLookupResult>('/api/v1/product-models/spec-lookup', input);
    } catch (err: unknown) {
      const api = err as { code?: string; message?: string };
      if (api.code === 'SERVICE_UNAVAILABLE' || api.code === 'RATE_LIMITED' || api.code === 'API_ERROR') {
        throw new Error(api.message ?? 'Gemini lookup failed.');
      }
      return null;
    }
  }

  static async resolveModelImage(modelId: string): Promise<ProductImageResolveResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<ProductImageResolveResult>(`/api/v1/product-models/${modelId}/resolve-image`, {});
  }

  static async fetchImageBlob(imageUrl: string): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob('/api/v1/product-images/proxy', { url: imageUrl });
  }
}
