import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type IntegrationServiceType = 'email' | 'sms' | 'whatsapp' | 'custom';

export interface IntegrationKeySummary {
  id: number;
  service_type: IntegrationServiceType;
  label: string;
  key_hint: string | null;
  is_active: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateIntegrationKeyRequest {
  service_type: IntegrationServiceType;
  label: string;
  api_key: string;
}

export interface UpdateIntegrationKeyRequest {
  label?: string;
  api_key?: string;
}

export const INTEGRATION_SERVICE_TYPES: { id: IntegrationServiceType; label: string }[] = [
  { id: 'email', label: 'Email' },
  { id: 'sms', label: 'SMS' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'custom', label: 'Custom service' },
];

export class IntegrationKeyService {
  static async listKeys(includeArchived = false): Promise<IntegrationKeySummary[]> {
    LoggingService.debug('API', 'Fetching integration API keys');
    const client = await ApiClientProvider.getClient();
    return client.get<IntegrationKeySummary[]>('/api/v1/admin/integration-keys', {
      include_archived: includeArchived,
    });
  }

  static async createKey(payload: CreateIntegrationKeyRequest): Promise<IntegrationKeySummary> {
    LoggingService.info('API', 'Creating integration API key', { service_type: payload.service_type });
    const client = await ApiClientProvider.getClient();
    return client.post<IntegrationKeySummary>('/api/v1/admin/integration-keys', payload);
  }

  static async updateKey(keyId: number, payload: UpdateIntegrationKeyRequest): Promise<IntegrationKeySummary> {
    LoggingService.info('API', 'Updating integration API key', { keyId });
    const client = await ApiClientProvider.getClient();
    return client.patch<IntegrationKeySummary>(`/api/v1/admin/integration-keys/${keyId}`, payload);
  }

  static async archiveKey(keyId: number): Promise<IntegrationKeySummary> {
    LoggingService.info('API', 'Archiving integration API key', { keyId });
    const client = await ApiClientProvider.getClient();
    return client.post<IntegrationKeySummary>(`/api/v1/admin/integration-keys/${keyId}/archive`);
  }

  static async restoreKey(keyId: number): Promise<IntegrationKeySummary> {
    LoggingService.info('API', 'Restoring integration API key', { keyId });
    const client = await ApiClientProvider.getClient();
    return client.post<IntegrationKeySummary>(`/api/v1/admin/integration-keys/${keyId}/restore`);
  }
}
