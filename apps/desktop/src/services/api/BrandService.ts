import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface Brand {
  id: number;
  name: string;
  short_name: string | null;
  logo_filename: string | null;
  display_order: number;
  is_active: boolean;
  /** EAN-as-serial mode: units of this brand may share a serial (the EAN). */
  allow_duplicate_serials: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CreateBrandRequest {
  name: string;
  short_name?: string | null;
  logo_filename?: string | null;
  display_order?: number;
  is_active?: boolean;
  allow_duplicate_serials?: boolean;
}

export interface UpdateBrandRequest {
  name?: string;
  short_name?: string | null;
  logo_filename?: string | null;
  display_order?: number;
  is_active?: boolean;
  allow_duplicate_serials?: boolean;
}

export class BrandService {
  static async listBrands(): Promise<Brand[]> {
    LoggingService.debug('API', 'Fetching brands list');
    const client = await ApiClientProvider.getClient();
    return client.get<Brand[]>('/api/v1/brands');
  }

  static async getBrand(id: number): Promise<Brand> {
    const client = await ApiClientProvider.getClient();
    return client.get<Brand>(`/api/v1/brands/${id}`);
  }

  static async createBrand(data: CreateBrandRequest): Promise<Brand> {
    const client = await ApiClientProvider.getClient();
    return client.post<Brand>('/api/v1/brands', data);
  }

  static async updateBrand(id: number, data: UpdateBrandRequest): Promise<Brand> {
    const client = await ApiClientProvider.getClient();
    return client.patch<Brand>(`/api/v1/brands/${id}`, data);
  }

  static async deleteBrand(id: number): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.delete(`/api/v1/brands/${id}`);
  }

  /** @deprecated Use deleteBrand — permanently removes the brand. */
  static async archiveBrand(id: number): Promise<void> {
    return BrandService.deleteBrand(id);
  }
}
