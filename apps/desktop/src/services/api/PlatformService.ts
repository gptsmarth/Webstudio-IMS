import { ApiClientProvider } from './ApiClientProvider';

export interface VersionIdentity {
  version: string;
  build_number: number;
  git_commit: string;
  git_short: string;
  release_date: string | null;
  release_channel: string;
  database_revision: string;
  product?: string;
}

export interface PlatformVersionInfo {
  version: string;
  build_number: number;
  git_commit: string;
  git_short: string;
  release_date: string | null;
  release_channel: string;
  database_revision: string;
  version_identity: VersionIdentity;
  backend_version: string;
  schema_version: string;
  api_version: string;
  build_version: string;
  min_desktop_version: string;
  min_mobile_version: string;
  desktop?: {
    latest_version: string;
    min_supported_version: string;
    release_channel: string;
    download_url?: string | null;
  };
  mobile?: Record<string, unknown>;
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
