import { ApiClient } from '@webstudio/api-client';
import type { ApiEnvelope, HealthLiveData } from '@webstudio/shared-kernel';
import { dispatchSetupRequired, isSetupRequiredApiError } from '../../lib/setupGuardEvents';
import { AuthTokenStore } from '../AuthTokenStore';
import { LoggingService } from '../LoggingService';

let refreshPromise: Promise<boolean> | null = null;

async function attemptTokenRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    const refreshToken = await AuthTokenStore.getRefreshToken();
    if (!refreshToken) return false;
    try {
      const { AuthenticationService } = await import('./AuthenticationService');
      await AuthenticationService.refresh();
      return true;
    } catch {
      await AuthTokenStore.clear();
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export class RetryingApiClient {
  private readonly inner: ApiClient;
  private readonly maxRetries = 3;

  constructor(inner: ApiClient) {
    this.inner = inner;
  }

  private async executeWithRetry<T>(operationName: string, fn: () => Promise<T>): Promise<T> {
    let lastError: unknown;
    let refreshed = false;
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (err: unknown) {
        const error = err as {
          response?: { status?: number; data?: unknown };
          code?: string;
          status?: number;
          message?: string;
          config?: { url?: string };
        };
        lastError = error;
        const status = error.response?.status ?? error.status ?? 0;
        const url = error.config?.url ?? operationName;
        const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/refresh');

        if (status === 401 && !isAuthRoute && !refreshed) {
          const renewed = await attemptTokenRefresh();
          if (renewed) {
            const token = await AuthTokenStore.getAccessToken();
            this.inner.setAccessToken(token);
            refreshed = true;
            continue;
          }
        }

        const isNetworkError =
          !error.response ||
          error.code === 'ECONNREFUSED' ||
          error.code === 'ERR_NETWORK' ||
          error.code === 'ECONNABORTED' ||
          status >= 500;
        // Never auto-retry mutating calls — a timed-out POST may already have
        // committed (e.g. product-model create), and retry creates orphans / duplicates.
        const isMutating = /^(POST|PUT|PATCH|DELETE)\b/i.test(operationName);

        if (isNetworkError && !isMutating && attempt < this.maxRetries) {
          LoggingService.warn(
            'API',
            `Network error during ${operationName} (Attempt ${attempt}/${this.maxRetries}). Retrying...`,
            {
              message: error.message ?? 'Unknown network error',
              code: error.code ?? 'UNKNOWN',
            },
          );
          // Exponential backoff delay (600ms, 1200ms)
          await new Promise((resolve) => setTimeout(resolve, attempt * 600));
          continue;
        }

        if (isSetupRequiredApiError(error)) {
          LoggingService.warn('API', 'System requires setup — clearing session and redirecting', {
            operation: operationName,
          });
          await AuthTokenStore.clear();
          dispatchSetupRequired('api_error');
        }

        LoggingService.error('API', `API call failed: ${operationName}`, {
          message: error.message ?? 'Unknown API error',
          status,
          data: error.response?.data,
        });
        throw error;
      }
    }
    throw lastError;
  }

  private unwrap<T>(res: unknown): T {
    if (res && typeof res === 'object' && 'data' in res && 'request_id' in res) {
      return (res as { data: T }).data;
    }
    return res as T;
  }

  setAccessToken(token: string | null): void {
    this.inner.setAccessToken(token);
  }

  async getHealthLive(): Promise<ApiEnvelope<HealthLiveData>> {
    return this.executeWithRetry('getHealthLive', () => this.inner.getHealthLive());
  }

  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const res = await this.executeWithRetry(`GET ${path}`, () =>
      this.inner.get<unknown>(path, params),
    );
    return this.unwrap<T>(res);
  }

  async getBlob(path: string, params?: Record<string, unknown>): Promise<Blob> {
    return this.executeWithRetry(`GET ${path}`, () => this.inner.getBlob(path, params));
  }

  async post<T>(path: string, data?: unknown): Promise<T> {
    const res = await this.executeWithRetry(`POST ${path}`, () =>
      this.inner.post<unknown>(path, data),
    );
    return this.unwrap<T>(res);
  }

  async postForm<T>(path: string, formData: FormData): Promise<T> {
    const res = await this.executeWithRetry(`POST ${path}`, () =>
      this.inner.postForm<unknown>(path, formData),
    );
    return this.unwrap<T>(res);
  }

  async put<T>(path: string, data?: unknown): Promise<T> {
    const res = await this.executeWithRetry(`PUT ${path}`, () =>
      this.inner.put<unknown>(path, data),
    );
    return this.unwrap<T>(res);
  }

  async delete<T>(path: string, data?: unknown): Promise<T> {
    const res = await this.executeWithRetry(`DELETE ${path}`, () =>
      this.inner.delete<unknown>(path, data),
    );
    return this.unwrap<T>(res);
  }

  async patch<T>(path: string, data?: unknown): Promise<T> {
    const res = await this.executeWithRetry(`PATCH ${path}`, () =>
      this.inner.patch<unknown>(path, data),
    );
    return this.unwrap<T>(res);
  }

  async getRaw<T, M = unknown>(
    path: string,
    params?: Record<string, unknown>,
  ): Promise<{ data: T; meta?: M }> {
    const res = await this.executeWithRetry(`GET ${path}`, () =>
      this.inner.get<unknown>(path, params),
    );
    if (res && typeof res === 'object' && 'data' in res) {
      return {
        data: (res as { data: T }).data,
        meta: (res as { meta?: M }).meta,
      };
    }
    return { data: res as T };
  }
}
