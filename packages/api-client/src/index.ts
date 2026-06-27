import axios, { type AxiosInstance } from 'axios';

import type { ApiEnvelope, HealthLiveData } from '@webstudio/shared-kernel';

export interface ApiClientOptions {
  baseUrl: string;
  clientVersion?: string;
  clientPlatform?: string;
}

export class ApiClient {
  private readonly http: AxiosInstance;

  constructor(options: ApiClientOptions) {
    this.http = axios.create({
      baseURL: options.baseUrl.replace(/\/$/, ''),
      timeout: 15000,
      headers: {
        'X-Client-Version': options.clientVersion ?? '0.1.0',
        'X-Client-Platform': options.clientPlatform ?? 'windows_desktop',
      },
    });
  }

  async getHealthLive(): Promise<ApiEnvelope<HealthLiveData>> {
    const response = await this.http.get<ApiEnvelope<HealthLiveData>>('/health/live');
    return response.data;
  }
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  return new ApiClient(options);
}
