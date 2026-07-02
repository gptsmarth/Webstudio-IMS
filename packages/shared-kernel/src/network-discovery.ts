export const DISCOVERY_SERVICE_TYPE = '_webstudio-ims._tcp.local.';
export const DEFAULT_BACKEND_PORT = 8000;

export interface DiscoveredServer {
  id: string;
  serverName: string;
  companyName: string;
  backendVersion: string;
  apiVersion: string;
  buildVersion: string;
  environment: string;
  port: number;
  host: string;
  url: string;
  lastSeen: string;
  status: 'online' | 'offline' | 'unknown';
}

export interface SavedServerRecord {
  url: string;
  friendlyName?: string;
  companyName?: string;
  hostname?: string;
  currentIp?: string;
  backendVersion?: string;
  lastConnectedAt?: string;
  lastSeenAt?: string;
}

export type ConnectionStageId =
  | 'host_resolution'
  | 'reachability'
  | 'http_connection'
  | 'backend_health'
  | 'api_compatibility'
  | 'authentication_endpoint';

export interface ConnectionStageResult {
  stage: ConnectionStageId;
  label: string;
  success: boolean;
  message: string;
}

export interface ConnectionDiagnosticsResult {
  success: boolean;
  url: string;
  stages: ConnectionStageResult[];
  failedStage?: ConnectionStageId;
  companyName?: string;
  backendVersion?: string;
  errorMessage?: string;
}

const HOSTNAME_PATTERN =
  /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(?:\.(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?))*$/;

export function normalizeServerHost(raw: string): string {
  const host = raw.trim();
  if (!host) {
    throw new Error('Host / IP address is required.');
  }
  if (/^\d{1,3}(?:\.\d{1,3}){3}$/.test(host)) {
    return host;
  }
  const lowered = host.toLowerCase().replace(/\.$/, '');
  if (!HOSTNAME_PATTERN.test(lowered)) {
    throw new Error(
      'Enter a valid IPv4 address, hostname, or mDNS name (for example WEBSTUDIO-SERVER.local).',
    );
  }
  return lowered;
}

export function normalizeServerUrl(raw: string, defaultPort = DEFAULT_BACKEND_PORT): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    throw new Error('Server address is required.');
  }

  let candidate = trimmed;
  if (!/^https?:\/\//i.test(candidate)) {
    candidate = `http://${candidate}`;
  }

  const parsed = new URL(candidate);
  const host = normalizeServerHost(parsed.hostname);
  const port = parsed.port ? Number(parsed.port) : defaultPort;
  return `http://${host}:${port}`.replace(/\/+$/, '');
}

export function extractHostnameFromUrl(url: string): string | undefined {
  try {
    return normalizeServerHost(new URL(url).hostname);
  } catch {
    return undefined;
  }
}

export function buildServerUrl(host: string, port: number): string {
  const normalizedHost = normalizeServerHost(host);
  return `http://${normalizedHost}:${port}`;
}

export const CONNECTION_STAGE_LABELS: Record<ConnectionStageId, string> = {
  host_resolution: 'Host Resolution',
  reachability: 'Reachability',
  http_connection: 'HTTP Connection',
  backend_health: 'Backend Health',
  api_compatibility: 'API Compatibility',
  authentication_endpoint: 'Authentication Endpoint',
};
