import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface SaleListItem {
  id: number;
  inventory_item_id: string | null;
  serial_number: string;
  brand_name: string;
  model_number: string;
  model_name: string;
  location_name: string;
  invoice_number: string;
  customer_name: string | null;
  payment_mode: string | null;
  sale_amount: number | null;
  sale_source: string;
  sold_at: string;
  recorded_by_user_id: number | null;
  recorded_by_display_name: string | null;
}

export interface SaleDetail extends SaleListItem {
  brand_id: number | null;
  product_model_id: string | null;
  location_id: number | null;
  color: string;
  cpu: string;
  ram_gb: number | null;
  storage_value: string;
  storage_unit: string;
  storage_type: string;
  notes: string | null;
  tally_company_name: string | null;
  tally_voucher_number: string | null;
  printed_invoice_number: string | null;
  tally_voucher_guid: string | null;
  tally_master_id: string | null;
  tally_voucher_type: string | null;
  created_at: string;
}

export interface SalesListParams {
  date_from?: string;
  date_to?: string;
  brand_id?: number;
  location_id?: number;
  user_id?: number;
  invoice_number?: string;
  customer_name?: string;
  payment_mode?: string;
  sale_source?: 'manual' | 'tally';
  search?: string;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface SalesListResult {
  items: SaleListItem[];
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

export class SalesService {
  static async listSales(params?: SalesListParams): Promise<SalesListResult> {
    LoggingService.debug('API', 'Fetching sales list', params as unknown as Record<string, unknown>);
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<SaleListItem[], ListMeta>('/api/v1/sales', {
      page: 1,
      page_size: 50,
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

  static async getSale(saleId: number): Promise<SaleDetail> {
    LoggingService.debug('API', 'Fetching sale detail', { saleId });
    const client = await ApiClientProvider.getClient();
    return client.get<SaleDetail>(`/api/v1/sales/${saleId}`);
  }
}
