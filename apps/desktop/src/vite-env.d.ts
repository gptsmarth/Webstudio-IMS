/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly MODE: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

type LogChannel = 'Renderer' | 'Main' | 'IPC' | 'API';
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface VersionInfo {
  appVersion: string;
  buildNumber: number;
  buildVersion: string;
  gitCommit: string;
  buildDate: string;
  releaseChannel: string;
  electronVersion: string;
  chromiumVersion: string;
  nodeVersion: string;
}

interface EnvConfig {
  mode: 'development' | 'production' | 'test';
  apiBaseUrl: string;
}

interface ApiNamespace {
  checkHealth: () => Promise<{ data?: { status?: string } }>;
}

interface ConfigNamespace {
  get: (key: string) => Promise<unknown>;
  set: (key: string, value: unknown) => Promise<void>;
  getEnv: () => Promise<EnvConfig>;
}

interface SystemNamespace {
  getVersionInfo: () => Promise<VersionInfo>;
  log: (channel: LogChannel, level: LogLevel, message: string, meta?: Record<string, unknown>) => Promise<void>;
  reportCrash: (errorDetails: Record<string, unknown>) => Promise<void>;
}

interface StorageNamespace {
  getItem: (key: string) => Promise<unknown>;
  setItem: (key: string, value: unknown) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
}

interface HostResolutionResult {
  host: string;
  resolvedIp: string | null;
  resolved: boolean;
  message: string;
}

interface DiscoveredServer {
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

interface NetworkNamespace {
  startDiscovery: () => Promise<void>;
  stopDiscovery: () => Promise<void>;
  getDiscoveredServers: () => Promise<DiscoveredServer[]>;
  resolveHost: (host: string) => Promise<HostResolutionResult>;
}

interface UpdateDownloadRequest {
  url: string;
  fileName: string;
  expectedSha256?: string;
}

interface UpdateNamespace {
  downloadArtifact: (request: UpdateDownloadRequest) => Promise<string>;
  installAndRestart: (installerPath: string) => Promise<void>;
}

interface Window {
  api?: ApiNamespace;
  config?: ConfigNamespace;
  system?: SystemNamespace;
  storage?: StorageNamespace;
  network?: NetworkNamespace;
  update?: UpdateNamespace;
}
