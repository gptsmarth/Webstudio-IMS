import { ApiClientProvider } from './ApiClientProvider';

export type ClientPlatform = 'desktop_windows' | 'desktop_macos';

export interface ClientUpdateArtifact {
  name: string;
  sha256: string | null;
  size_bytes: number | null;
  download_url: string;
}

export interface ClientUpdateCheckResult {
  platform: string;
  installed_version: string;
  latest_version: string;
  min_supported_version: string;
  update_available: boolean;
  mandatory: boolean;
  release_channel: string;
  release_notes: string | null;
  published_at: string | null;
  distribution_mode: 'installer' | 'apk_sideload' | 'app_store_notification';
  artifact: ClientUpdateArtifact | null;
}

export class ClientUpdateService {
  static resolveDesktopPlatform(): ClientPlatform {
    if (typeof navigator !== 'undefined' && navigator.platform?.toLowerCase().includes('win')) {
      return 'desktop_windows';
    }
    return 'desktop_macos';
  }

  static async checkForUpdates(installedVersion: string): Promise<ClientUpdateCheckResult> {
    const client = await ApiClientProvider.getClient();
    const platform = this.resolveDesktopPlatform();
    const params = new URLSearchParams({
      platform,
      current_version: installedVersion,
    });
    return client.get<ClientUpdateCheckResult>(`/api/v1/client-updates/check?${params.toString()}`);
  }

  static resolveAbsoluteDownloadUrl(relativeUrl: string, apiBaseUrl: string): string {
    if (relativeUrl.startsWith('http://') || relativeUrl.startsWith('https://')) {
      return relativeUrl;
    }
    const base = apiBaseUrl.replace(/\/$/, '');
    const path = relativeUrl.startsWith('/') ? relativeUrl : `/${relativeUrl}`;
    return `${base}${path}`;
  }
}
