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

  setAccessToken(token: string | null): void {
    if (token) {
      this.http.defaults.headers.common.Authorization = `Bearer ${token}`;
    } else {
      delete this.http.defaults.headers.common.Authorization;
    }
  }

  async getHealthLive(): Promise<ApiEnvelope<HealthLiveData>> {
    const response = await this.http.get<ApiEnvelope<HealthLiveData>>('/health/live');
    return response.data;
  }

  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.http.get<T>(path, { params });
    return response.data;
  }

  async getBlob(path: string, params?: Record<string, unknown>): Promise<Blob> {
    const response = await this.http.get<Blob>(path, {
      params,
      responseType: 'blob',
    });
    return response.data;
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    const response = await this.http.post<T>(path, data);
    return response.data;
  }

  async postForm<T>(path: string, formData: FormData): Promise<T> {
    const response = await this.http.post<T>(path, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }

  async put<T>(path: string, data?: unknown): Promise<T> {
    const response = await this.http.put<T>(path, data);
    return response.data;
  }

  async delete<T>(path: string): Promise<T> {
    const response = await this.http.delete<T>(path);
    return response.data;
  }

  async patch<T>(path: string, data?: unknown): Promise<T> {
    const response = await this.http.patch<T>(path, data);
    return response.data;
  }
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  return new ApiClient(options);
}
