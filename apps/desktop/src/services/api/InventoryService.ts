import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type InventoryStatus = 'received' | 'available' | 'reserved' | 'sold';
export type StorageUnit = 'GB' | 'TB';
export type StorageType = 'SSD' | 'HDD';

export interface InventoryItemDetail {
  id: string;
  serial_number: string;
  product_model_id: string;
  brand_id: number;
  brand_name: string;
  model_number: string;
  model_name: string;
  cpu: string;
  gpu: string | null;
  ram_gb: number;
  storage_value: string;
  storage_unit: StorageUnit;
  storage_type: StorageType;
  color: string;
  current_location_id: number;
  current_location_name: string;
  status: InventoryStatus;
  is_archived: boolean;
  purchase_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryListParams {
  brand_id?: number;
  product_model_id?: string;
  current_location_id?: number;
  status?: InventoryStatus;
  is_archived?: boolean;
  include_archived?: boolean;
  serial_number?: string;
  brand?: string;
  product_model?: string;
  location?: string;
  search?: string;
  color?: string;
  purchase_date_from?: string;
  purchase_date_to?: string;
  created_at_from?: string;
  created_at_to?: string;
  page?: number;
  page_size?: number;
  sort?: string;
}

export interface InventoryListResult {
  items: InventoryItemDetail[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

interface ListMeta {
  page?: number;
  page_size?: number;
  total_items?: number;
  total_pages?: number;
}

export interface CreateInventoryItemRequest {
  serial_number: string;
  product_model_id: string;
  color: string;
  current_location_id: number;
  status?: InventoryStatus;
  purchase_date?: string | null;
}

export interface UpdateInventoryItemRequest {
  serial_number?: string;
  product_model_id?: string;
  color?: string;
  status?: InventoryStatus;
  purchase_date?: string | null;
}

export interface MarkSoldRequest {
  invoice_number: string;
  customer_name: string;
  payment_mode: string;
  sale_date: string;
  sale_amount?: number | null;
  remarks?: string | null;
}

export interface SaleDetail {
  id: number;
  inventory_item_id: string;
  serial_number: string;
  sale_source: string;
  sold_at: string;
  invoice_number: string;
  customer_name: string | null;
  payment_mode: string | null;
  sale_amount: number | null;
  notes: string | null;
  recorded_by_user_id: number | null;
  created_at: string;
}

export interface MarkSoldResponse {
  inventory: InventoryItemDetail;
  sale: SaleDetail;
}

export class InventoryService {
  static async listItems(params?: InventoryListParams): Promise<InventoryListResult> {
    LoggingService.debug(
      'API',
      'Fetching inventory items list',
      params as unknown as Record<string, unknown>,
    );
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<InventoryItemDetail[], ListMeta>('/api/v1/inventory', {
      page: 1,
      page_size: 50,
      sort: 'updated_at:desc',
      ...params,
    } as Record<string, unknown>);
    return {
      items: response.data,
      page: response.meta?.page ?? params?.page ?? 1,
      page_size: response.meta?.page_size ?? params?.page_size ?? 50,
      total_items: response.meta?.total_items ?? response.data.length,
      total_pages: response.meta?.total_pages ?? 1,
    };
  }

  static async getItem(id: string): Promise<InventoryItemDetail> {
    LoggingService.debug('API', `Fetching inventory item ${id}`);
    const client = await ApiClientProvider.getClient();
    return client.get<InventoryItemDetail>(`/api/v1/inventory/${id}`);
  }

  static async getBySerial(serial: string): Promise<InventoryItemDetail> {
    const client = await ApiClientProvider.getClient();
    return client.get<InventoryItemDetail>(
      `/api/v1/inventory/by-serial/${encodeURIComponent(serial)}`,
    );
  }

  static async createItem(data: CreateInventoryItemRequest): Promise<InventoryItemDetail> {
    LoggingService.info(
      'API',
      'Creating inventory item',
      data as unknown as Record<string, unknown>,
    );
    const client = await ApiClientProvider.getClient();
    return client.post<InventoryItemDetail>(
      '/api/v1/inventory',
      data as unknown as Record<string, unknown>,
    );
  }

  static async updateItem(
    id: string,
    data: UpdateInventoryItemRequest,
  ): Promise<InventoryItemDetail> {
    LoggingService.info(
      'API',
      `Updating inventory item ${id}`,
      data as unknown as Record<string, unknown>,
    );
    const client = await ApiClientProvider.getClient();
    return client.patch<InventoryItemDetail>(
      `/api/v1/inventory/${id}`,
      data as unknown as Record<string, unknown>,
    );
  }

  static async archiveItem(id: string): Promise<InventoryItemDetail> {
    const client = await ApiClientProvider.getClient();
    return client.post<InventoryItemDetail>(`/api/v1/inventory/${id}/archive`);
  }

  static async restoreItem(id: string): Promise<InventoryItemDetail> {
    const client = await ApiClientProvider.getClient();
    return client.post<InventoryItemDetail>(`/api/v1/inventory/${id}/restore`);
  }

  static async transferLocation(id: string, locationId: number): Promise<InventoryItemDetail> {
    const client = await ApiClientProvider.getClient();
    return client.patch<InventoryItemDetail>(`/api/v1/inventory/${id}/location`, {
      location_id: locationId,
    });
  }

  static async markSold(id: string, data: MarkSoldRequest): Promise<MarkSoldResponse> {
    const client = await ApiClientProvider.getClient();
    return client.patch<MarkSoldResponse>(`/api/v1/inventory/${id}/mark-sold`, data);
  }
}
