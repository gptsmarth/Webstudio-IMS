import { ApiClientProvider } from './ApiClientProvider';

export interface PlatformVersionInfo {
  backend_version: string;
  schema_version: string;
  api_version: string;
  build_version: string;
  min_desktop_version: string;
  min_mobile_version: string;
}

export interface PlatformCapabilities {
  installed_version: string;
  api_version: string;
  modules: Record<string, boolean>;
  tally_enabled: boolean;
  backup_enabled: boolean;
  reports_enabled: boolean;
  feature_flags: Record<string, boolean>;
}

export class PlatformService {
  static async getVersion(): Promise<PlatformVersionInfo> {
    const client = await ApiClientProvider.getClient();
    return client.get<PlatformVersionInfo>('/api/v1/version');
  }

  static async getCapabilities(): Promise<PlatformCapabilities> {
    const client = await ApiClientProvider.getClient();
    return client.get<PlatformCapabilities>('/api/v1/capabilities');
  }
}
