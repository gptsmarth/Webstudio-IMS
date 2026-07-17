import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';
import type { CreateProductModelRequest } from './ProductModelService';
import type { InventoryStatus } from './InventoryService';

export interface PurchaseTaxBreakdown {
  subtotal: string | number | null;
  discount_amount: string | number | null;
  round_off: string | number | null;
  cgst_amount: string | number | null;
  sgst_amount: string | number | null;
  igst_amount: string | number | null;
  cess_amount: string | number | null;
  grand_total: string | number | null;
}

export interface PurchaseQueueItem {
  id: number;
  supplier_name: string | null;
  voucher_date: string | null;
  voucher_number: string;
  invoice_number: string | null;
  reference_number: string | null;
  voucher_guid: string;
  voucher_type: string | null;
  grand_total: string | number | null;
  taxes: PurchaseTaxBreakdown;
  status: string;
  group_count: number;
  imported_group_count: number;
  pending_group_count: number;
}

export interface PurchaseSerialCell {
  serial_number: string;
  is_duplicate: boolean;
  existing_status: string | null;
}

export interface PurchaseModelGroup {
  group_key: string;
  stock_item_name: string;
  quantity: number;
  serial_source: string | null;
  serials: PurchaseSerialCell[];
  line_total: string | number | null;
  imported: boolean;
  product_model_id: string | null;
  duplicate_count: number;
}

export interface PurchaseVoucherDetail {
  id: number;
  supplier_name: string | null;
  voucher_date: string | null;
  voucher_number: string;
  invoice_number: string | null;
  reference_number: string | null;
  voucher_guid: string;
  voucher_type: string | null;
  narration: string | null;
  taxes: PurchaseTaxBreakdown;
  grand_total: string | number | null;
  status: string;
  groups: PurchaseModelGroup[];
}

export interface MatchedModel {
  id: string;
  model_number: string;
  model_name: string;
  category: string;
  is_active: boolean;
  // 'exact' — normalized model number matches exactly (auto-selectable).
  // 'partial' — one model number contains the other (a suggestion the operator
  //   must confirm, e.g. an IMS entry with an extra base-model suffix).
  match_kind?: 'exact' | 'partial';
}

export interface MatchModelResponse {
  normalized_model_number: string;
  matches: MatchedModel[];
  auto_selected_model_id: string | null;
}

export interface AccessoryMatch {
  id: string;
  model_number: string;
  model_name: string;
  part_number: string | null;
  accessory_kind: string | null;
  category: string;
  is_active: boolean;
  score: number;
}

export interface MatchAccessoryResponse {
  normalized_query: string;
  matches: AccessoryMatch[];
  auto_selected_model_id: string | null;
}

export interface PurchaseImportRequest {
  voucher_id: number;
  group_key: string;
  brand_id: number;
  mode: 'existing' | 'new';
  product_model_id?: string;
  new_product_model?: CreateProductModelRequest;
  serial_numbers: string[];
  color: string;
  current_location_id: number;
  status?: InventoryStatus;
  purchase_price?: number | null;
}

export interface PurchaseImportResponse {
  product_model_id: string;
  imported_count: number;
  voucher_status: string;
  group_key: string;
  existing_model: boolean;
}

export interface PurchaseIgnoreResponse {
  voucher_id: number;
  status: string;
}

export interface PurchaseBackfillResponse {
  fetched: number;
  new: number;
  from_date: string;
  to_date: string | null;
}

export class PurchaseService {
  static async listQueue(status?: string): Promise<PurchaseQueueItem[]> {
    LoggingService.debug('API', 'Fetching purchase queue');
    const client = await ApiClientProvider.getClient();
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return client.get<PurchaseQueueItem[]>(`/api/v1/purchase/queue${query}`);
  }

  static async getVoucher(voucherId: number): Promise<PurchaseVoucherDetail> {
    const client = await ApiClientProvider.getClient();
    return client.get<PurchaseVoucherDetail>(`/api/v1/purchase/queue/${voucherId}`);
  }

  static async matchModel(brandId: number, modelNumber: string): Promise<MatchModelResponse> {
    const client = await ApiClientProvider.getClient();
    return client.post<MatchModelResponse>('/api/v1/purchase/match-model', {
      brand_id: brandId,
      model_number: modelNumber,
    });
  }

  static async matchAccessory(brandId: number, query: string): Promise<MatchAccessoryResponse> {
    const client = await ApiClientProvider.getClient();
    return client.post<MatchAccessoryResponse>('/api/v1/purchase/match-accessory', {
      brand_id: brandId,
      query,
    });
  }

  static async importGroup(data: PurchaseImportRequest): Promise<PurchaseImportResponse> {
    LoggingService.info('API', 'Importing purchase model group', {
      voucher_id: data.voucher_id,
      group_key: data.group_key,
      mode: data.mode,
    });
    const client = await ApiClientProvider.getClient();
    return client.post<PurchaseImportResponse>(
      '/api/v1/purchase/import',
      data as unknown as Record<string, unknown>,
    );
  }

  static async ignoreVoucher(voucherId: number): Promise<PurchaseIgnoreResponse> {
    LoggingService.info('API', 'Ignoring purchase voucher', { voucher_id: voucherId });
    const client = await ApiClientProvider.getClient();
    return client.post<PurchaseIgnoreResponse>(`/api/v1/purchase/queue/${voucherId}/ignore`, {});
  }

  static async backfill(fromDate: string, toDate?: string): Promise<PurchaseBackfillResponse> {
    LoggingService.info('API', 'Backfilling purchases from Tally', {
      from_date: fromDate,
      to_date: toDate ?? null,
    });
    const client = await ApiClientProvider.getClient();
    return client.post<PurchaseBackfillResponse>('/api/v1/purchase/backfill', {
      from_date: fromDate,
      to_date: toDate ?? null,
    });
  }
}
