import { createApiClient } from '@webstudio/api-client';
import { ConfigService } from '../ConfigService';
import { AuthTokenStore } from '../AuthTokenStore';
import { VersionService } from '../VersionService';
import { ClientUpdateService } from './ClientUpdateService';
import { RetryingApiClient } from './client';

function resolveApiClientPlatform(): string {
  return ClientUpdateService.resolveDesktopPlatform() === 'desktop_windows'
    ? 'windows_desktop'
    : 'macos_desktop';
}

export class ApiClientProvider {
  private static instance: RetryingApiClient | null = null;
  private static lastUrl: string | null = null;

  static async getClient(): Promise<RetryingApiClient> {
    const env = await ConfigService.getEnvironment();
    const versionInfo = await VersionService.getVersionInfo();
    if (!this.instance || this.lastUrl !== env.apiBaseUrl) {
      this.lastUrl = env.apiBaseUrl;
      const rawClient = createApiClient({
        baseUrl: env.apiBaseUrl,
        clientVersion: versionInfo.appVersion,
        clientPlatform: resolveApiClientPlatform(),
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
