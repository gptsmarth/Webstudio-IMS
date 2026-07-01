import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import type { StorageType, StorageUnit } from './InventoryService';

export type ProductModelStatus = 'active' | 'archived';

export interface ProductModel {
  id: string;
  brand_id: number;
  brand_name: string | null;
  model_number: string;
  model_name: string;
  cpu: string;
  gpu: string | null;
  ram_gb: number;
  storage_value: string;
  storage_unit: StorageUnit;
  storage_type: StorageType;
  status: ProductModelStatus;
  display: string | null;
  color_options: string | null;
  product_image_url: string | null;
  search_aliases: string | null;
  notes: string | null;
  purchase_price?: number | null;
  selling_price?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreateProductModelRequest {
  brand_id: number;
  model_number: string;
  model_name: string;
  cpu: string;
  gpu?: string | null;
  ram_gb: number;
  storage_value: number | string;
  storage_unit: StorageUnit;
  storage_type: StorageType;
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

export interface ProductModelListParams {
  brand_id?: number;
  active?: boolean;
  archived?: boolean;
}

export class ProductModelService {
  static async listModels(brandIdOrParams?: number | ProductModelListParams): Promise<ProductModel[]> {
    LoggingService.debug('API', 'Fetching product models list');
    const client = await ApiClientProvider.getClient();
    const params = typeof brandIdOrParams === 'number'
      ? { brand_id: brandIdOrParams }
      : brandIdOrParams;
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

  static async updateModel(id: string, data: UpdateProductModelRequest): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ProductModel>(`/api/v1/product-models/${id}`, data);
  }

  static async updateSellingPrice(id: string, data: UpdateSellingPriceRequest): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.patch<ProductModel>(`/api/v1/product-models/${id}/selling-price`, data);
  }

  static async deleteModel(id: string): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.delete(`/api/v1/product-models/${id}`);
  }

  /** @deprecated Use deleteModel — permanently removes the model and its inventory units. */
  static async archiveModel(id: string): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.post(`/api/v1/product-models/${id}/archive`, {});
  }

  static async restoreModel(id: string): Promise<ProductModel> {
    const client = await ApiClientProvider.getClient();
    return client.post<ProductModel>(`/api/v1/product-models/${id}/restore`, {});
  }
}
