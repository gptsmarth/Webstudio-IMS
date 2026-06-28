import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface HealthLive {
  status: string;
  version: string;
  api_version: string;
}

export interface HealthReady {
  status: 'ready' | 'not_ready';
  checks: {
    database: string;
    migrations: string;
    disk_space: string;
  };
}

export class HealthService {
  static async getLive(): Promise<HealthLive> {
    LoggingService.debug('API', 'Health live check');
    const client = await ApiClientProvider.getClient();
    return client.get<HealthLive>('/health/live');
  }

  static async getReady(): Promise<HealthReady> {
    const client = await ApiClientProvider.getClient();
    try {
      return await client.get<HealthReady>('/health/ready');
    } catch {
      return {
        status: 'not_ready',
        checks: { database: 'failed', migrations: 'unknown', disk_space: 'unknown' },
      };
    }
  }
}
