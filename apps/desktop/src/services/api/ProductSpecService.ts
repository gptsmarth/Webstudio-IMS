import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import type { StorageType, StorageUnit } from './InventoryService';
import type { AccessoryKind, AccessoryIdentifierType } from '../../lib/productCategory';

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

export interface AccessorySpecLookupResult {
  model_name: string;
  model_number: string | null;
  part_number: string | null;
  accessory_kind: AccessoryKind | null;
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

export class SpecLookupError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = 'SpecLookupError';
    this.code = code;
  }
}

const RETRIABLE_SPEC_LOOKUP_CODES = new Set([
  'RATE_LIMITED',
  'API_ERROR',
  'TIMEOUT',
  'QUOTA_EXCEEDED',
]);

// Not retriable (retrying won't help until the admin fixes it), but still needs its own
// actionable message rather than being folded into a generic "no match" result — e.g. a
// missing/cleared Gemini API key should never look identical to "this SKU wasn't found."
const ACTIONABLE_SPEC_LOOKUP_CODES = new Set(['NOT_CONFIGURED']);

export function isRetriableSpecLookupError(err: unknown): boolean {
  if (err instanceof SpecLookupError) {
    return RETRIABLE_SPEC_LOOKUP_CODES.has(err.code);
  }
  const code = (err as { code?: string }).code;
  return typeof code === 'string' && RETRIABLE_SPEC_LOOKUP_CODES.has(code);
}

function isThrowableSpecLookupCode(code: string | undefined): boolean {
  return Boolean(
    code &&
    (RETRIABLE_SPEC_LOOKUP_CODES.has(code) ||
      ACTIONABLE_SPEC_LOOKUP_CODES.has(code) ||
      code === 'SERVICE_UNAVAILABLE'),
  );
}

export class ProductSpecService {
  static async lookupSpec(input: {
    model_number: string;
    model_name?: string;
    brand_name?: string;
    force_refresh?: boolean;
  }): Promise<ProductSpecLookupResult | null> {
    LoggingService.info('API', 'Looking up product spec via Gemini', {
      model: input.model_number,
      forceRefresh: Boolean(input.force_refresh),
    });
    const client = await ApiClientProvider.getClient();
    try {
      return await client.post<ProductSpecLookupResult>(
        '/api/v1/product-models/spec-lookup',
        input,
      );
    } catch (err: unknown) {
      const api = err as { code?: string; message?: string };
      if (isThrowableSpecLookupCode(api.code)) {
        throw new SpecLookupError(api.code!, api.message ?? 'Gemini lookup failed.');
      }
      return null;
    }
  }

  static async lookupAccessorySpec(input: {
    identifier: string;
    identifier_type?: AccessoryIdentifierType;
    brand_name?: string;
    model_name?: string;
    force_refresh?: boolean;
  }): Promise<AccessorySpecLookupResult | null> {
    LoggingService.info('API', 'Looking up accessory spec via Gemini', { id: input.identifier });
    const client = await ApiClientProvider.getClient();
    try {
      return await client.post<AccessorySpecLookupResult>(
        '/api/v1/product-models/accessory-spec-lookup',
        input,
      );
    } catch (err: unknown) {
      const api = err as { code?: string; message?: string };
      if (isThrowableSpecLookupCode(api.code)) {
        throw new SpecLookupError(api.code!, api.message ?? 'Gemini lookup failed.');
      }
      return null;
    }
  }

  static async resolveModelImage(modelId: string): Promise<ProductImageResolveResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<ProductImageResolveResult>(
      `/api/v1/product-models/${modelId}/resolve-image`,
      {},
    );
  }

  static async fetchImageBlob(imageUrl: string): Promise<Blob> {
    const client = await ApiClientProvider.getClient();
    return client.getBlob('/api/v1/product-images/proxy', { url: imageUrl });
  }
}
