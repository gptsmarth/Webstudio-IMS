import { LoggingService } from '../LoggingService';
import { ApiClientProvider } from './ApiClientProvider';

export interface OperationsDashboard {
  total_available_inventory: number;
  as_of: string;
}

export interface DistributionGroup {
  id: string;
  name: string;
  available: number;
  sold: number;
  total: number;
}

export interface DashboardDistribution {
  total_available_inventory: number;
  by_brand: DistributionGroup[];
  by_location: DistributionGroup[];
  by_product_model: DistributionGroup[];
  as_of: string;
}

export interface RecentActivityEntry {
  id: string;
  activity_type: string;
  entity_type: string;
  entity_id: string;
  description: string | null;
  actor_display_name: string | null;
  actor_role: string | null;
  created_at: string;
}

export class DashboardService {
  static async getOperationsSnapshot(): Promise<OperationsDashboard> {
    LoggingService.debug('API', 'Fetching operations dashboard snapshot');
    const client = await ApiClientProvider.getClient();
    return client.get<OperationsDashboard>('/api/v1/dashboard');
  }

  static async getDistribution(): Promise<DashboardDistribution> {
    LoggingService.debug('API', 'Fetching dashboard distribution');
    const client = await ApiClientProvider.getClient();
    return client.get<DashboardDistribution>('/api/v1/dashboard/distribution');
  }

  static async getRecentActivity(limit = 8): Promise<RecentActivityEntry[]> {
    LoggingService.debug('API', 'Fetching dashboard recent activity');
    const client = await ApiClientProvider.getClient();
    return client.get<RecentActivityEntry[]>('/api/v1/dashboard/recent-activity', { limit });
  }
}
