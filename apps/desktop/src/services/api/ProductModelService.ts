import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import { isConflictError } from '../../lib/apiError';
import type { StorageType, StorageUnit } from './InventoryService';
import type { AccessoryKind, ProductCategory } from '../../lib/productCategory';

export type ProductModelStatus = 'active' | 'archived';

export interface ProductModel {
  id: string;
  brand_id: number;
  brand_name: string | null;
  category: ProductCategory;
  accessory_kind: AccessoryKind | null;
  part_number: string | null;
  model_number: string;
  model_name: string;
  cpu: string | null;
  gpu: string | null;
  ram_gb: number | null;
  storage_value: string | null;
  storage_unit: StorageUnit | null;
  storage_type: StorageType | null;
  status: ProductModelStatus;
  display: string | null;
  color_options: string | null;
  product_image_url: string | null;
  search_aliases: string | null;
  notes: string | null;
  purchase_price?: number | null;
  selling_price?: number | null;
  live_price?: number | null;
  live_price_status?:
    | 'ok'
    | 'not_found'
    | 'error'
    | 'not_configured'
    | 'not_applicable'
    | 'manual'
    | null;
  live_price_source_url?: string | null;
  live_price_checked_at?: string | null;
  live_price_updated_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreateProductModelRequest {
  brand_id: number;
  category?: ProductCategory;
  accessory_kind?: AccessoryKind | null;
  part_number?: string | null;
  model_number: string;
  model_name: string;
  cpu?: string | null;
  gpu?: string | null;
  ram_gb?: number | null;
  storage_value?: number | string | null;
  storage_unit?: StorageUnit | null;
  storage_type?: StorageType | null;
  status?: ProductModelStatus;
  display?: string | null;
  color_options?: string | null;
  product_image_url?: string | null;
  search_aliases?: string | null;
  notes?: string | null;
  purchase_price?: number | null;
  selling_price?: number | null;
}

export type UpdateProductModelRequest = Partial<CreateProductModelRequest>;

export interface UpdateSellingPriceRequest {
  selling_price?: number | null;
}

export interface UpdateLivePriceRequest {
  live_price?: number | null;
}

export interface ProductModelListParams {
  brand_id?: number;
  category?: ProductCategory;
  active?: boolean;
  archived?: boolean;
}

export class ProductModelService {
  static async listModels(
    brandIdOrParams?: number | ProductModelListParams,
  ): Promise<ProductModel[]> {
    LoggingService.debug('API', 'Fetching product models list');
    const client = await ApiClientProvider.getClient();
    const params =
      typeof brandIdOrParams === 'number' ? { brand_id: brandIdOrParams } : brandIdOrParams;
    return client.get<ProductModel[]>('/api/v1/product-models', params as Record<string, unknown>);
  }

  static async getModel(id: string): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.get<ProductModel>(`/api/v1/product-models/${id}`);
  }

  static async createModel(data: CreateProductModelRequest): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.post<ProductModel>('/api/v1/product-models', data);
  }

  /**
   * Create a product model, or return the existing one when the brand+model_number
   * unique constraint already holds (409). Used by add-inventory wizards so a
   * prior timed-out create does not abort serial/unit creation.
   */
  static async createOrFindModel(data: CreateProductModelRequest): Promise<ProductModel> {
    try {
      return await ProductModelService.createModel(data);
    } catch (err: unknown) {
      if (!isConflictError(err)) throw err;
      const models = await ProductModelService.listModels({
        brand_id: data.brand_id,
        archived: false,
      });
      const needle = data.model_number.trim().toLowerCase();
      const existing = models.find((model) => model.model_number.trim().toLowerCase() === needle);
      if (!existing) throw err;
      LoggingService.warn(
        'API',
        `Product model already exists; reusing ${existing.id} for ${data.model_number}`,
      );
      return existing;
    }
  }

  static async updateModel(id: string, data: UpdateProductModelRequest): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ProductModel>(`/api/v1/product-models/${id}`, data);
  }

  static async updateSellingPrice(
    id: string,
    data: UpdateSellingPriceRequest,
  ): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ProductModel>(`/api/v1/product-models/${id}/selling-price`, data);
  }

  /** Manually enter/correct the ASUS live price — same trust tier as editing
   * the selling price. The next successful automatic refresh overwrites it. */
  static async updateLivePrice(id: string, data: UpdateLivePriceRequest): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ProductModel>(`/api/v1/product-models/${id}/live-price`, data);
  }

  static async deleteModel(id: string): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.delete(`/api/v1/product-models/${id}`);
  }

  static async refreshLivePrice(id: string): Promise<{ scheduled: boolean }> {
    const client = await ApiClientProvider.getClient();
    return client.post<{ scheduled: boolean }>(
      `/api/v1/product-models/${id}/refresh-live-price`,
      {},
    );
  }

  static async refreshAllLivePrices(): Promise<{ scheduled: number }> {
    const client = await ApiClientProvider.getClient();
    return client.post<{ scheduled: number }>('/api/v1/product-models/refresh-live-prices', {});
  }

  static async getLivePriceRefreshStatus(): Promise<AsusPriceRefreshStatus> {
    const client = await ApiClientProvider.getClient();
    return client.get<AsusPriceRefreshStatus>('/api/v1/product-models/refresh-live-prices/status');
  }

  static async retryFailedLivePrices(): Promise<{ scheduled: number }> {
    const client = await ApiClientProvider.getClient();
    return client.post<{ scheduled: number }>(
      '/api/v1/product-models/refresh-live-prices/retry-failed',
      {},
    );
  }
}

export interface AsusPriceRefreshStatus {
  total: number;
  completed: number;
  in_progress: number;
  started_at: string | null;
  finished_at: string | null;
  failed_model_ids: string[];
}
