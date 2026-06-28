import { createApiClient } from '@webstudio/api-client';
import { ConfigService } from '../ConfigService';
import { AuthTokenStore } from '../AuthTokenStore';
import { RetryingApiClient } from './client';

export class ApiClientProvider {
  private static instance: RetryingApiClient | null = null;
  private static lastUrl: string | null = null;

  static async getClient(): Promise<RetryingApiClient> {
    const env = await ConfigService.getEnvironment();
    if (!this.instance || this.lastUrl !== env.apiBaseUrl) {
      this.lastUrl = env.apiBaseUrl;
      const rawClient = createApiClient({
        baseUrl: env.apiBaseUrl,
        clientVersion: '0.1.0',
        clientPlatform: 'macos_desktop',
      });
      this.instance = new RetryingApiClient(rawClient);
    }

    const token = await AuthTokenStore.getAccessToken();
    this.instance.setAccessToken(token);
    return this.instance;
  }

  static reset(): void {
    this.instance = null;
    this.lastUrl = null;
  }
}
