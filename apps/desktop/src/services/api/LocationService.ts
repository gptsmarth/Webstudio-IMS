import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type LocationType = 'retail_floor' | 'warehouse' | 'other';

export interface Location {
  id: number;
  name: string;
  location_type: LocationType;
  is_active: boolean;
  sort_order: number | null;
  branch_id: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreateLocationRequest {
  name: string;
  location_type: LocationType;
  is_active?: boolean;
  sort_order?: number | null;
  branch_id?: number | null;
}

export interface UpdateLocationRequest {
  name?: string;
  location_type?: LocationType;
  is_active?: boolean;
  sort_order?: number | null;
  branch_id?: number | null;
}

export interface LocationArchivePreview {
  movable_inventory_count: number;
  requires_transfer: boolean;
}

export interface ArchiveLocationRequest {
  transfer_to_location_id?: number | null;
}

export class LocationService {
  static async listLocations(): Promise<Location[]> {
    LoggingService.debug('API', 'Fetching locations list');
    const client = await ApiClientProvider.getClient();
    return client.get<Location[]>('/api/v1/locations');
  }

  static async getLocation(id: number): Promise<Location> {
    const client = await ApiClientProvider.getClient();
    return client.get<Location>(`/api/v1/locations/${id}`);
  }

  static async createLocation(data: CreateLocationRequest): Promise<Location> {
    const client = await ApiClientProvider.getClient();
    return client.post<Location>('/api/v1/locations', data);
  }

  static async updateLocation(id: number, data: UpdateLocationRequest): Promise<Location> {
    const client = await ApiClientProvider.getClient();
    return client.patch<Location>(`/api/v1/locations/${id}`, data);
  }

  static async archiveLocation(id: number, data: ArchiveLocationRequest = {}): Promise<Location> {
    const client = await ApiClientProvider.getClient();
    return client.post<Location>(`/api/v1/locations/${id}/archive`, data);
  }

  static async getArchivePreview(id: number): Promise<LocationArchivePreview> {
    const client = await ApiClientProvider.getClient();
    return client.get<LocationArchivePreview>(`/api/v1/locations/${id}/archive-preview`);
  }

  static async restoreLocation(id: number): Promise<Location> {
    const client = await ApiClientProvider.getClient();
    return client.post<Location>(`/api/v1/locations/${id}/restore`, {});
  }
}
