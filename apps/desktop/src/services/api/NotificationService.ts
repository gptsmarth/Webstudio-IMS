import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type NotificationSeverity = 'error' | 'warning' | 'info';

export interface NotificationDetail {
  id: number;
  notification_type: string;
  title: string;
  description: string;
  category: string;
  severity: NotificationSeverity;
  status: string;
  is_read: boolean;
  is_resolved: boolean;
  serial_number: string | null;
  created_at: string;
}

export interface NotificationListResult {
  items: NotificationDetail[];
  total_items: number;
}

interface ListMeta {
  page?: number;
  page_size?: number;
  total_items?: number;
  total_pages?: number;
}

export class NotificationService {
  static async listNotifications(params?: {
    is_resolved?: boolean;
    page_size?: number;
  }): Promise<NotificationListResult> {
    LoggingService.debug('API', 'Fetching notifications');
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<NotificationDetail[], ListMeta>('/api/v1/notifications', {
      is_resolved: params?.is_resolved ?? false,
      page: 1,
      page_size: params?.page_size ?? 20,
    });
    return {
      items: response.data,
      total_items: response.meta?.total_items ?? response.data.length,
    };
  }

  static async markRead(id: number): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.patch(`/api/v1/notifications/${id}/read`);
  }

  static async resolve(id: number): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.patch(`/api/v1/notifications/${id}/resolve`);
  }
}
