export const API_VERSION = '1.0';
export const APP_VERSION = '0.1.0';

export * from './network-discovery';

export type ClientPlatform =
  | 'windows_desktop'
  | 'macos_desktop'
  | 'android'
  | 'excel_sync'
  | 'tally_sync';

export interface ApiEnvelope<T> {
  data: T;
  meta: Record<string, unknown> | null;
  request_id: string;
  correlation_id: string;
  timestamp: string;
}

export interface HealthLiveData {
  status: string;
  version: string;
  api_version: string;
  min_client_version: string;
}
