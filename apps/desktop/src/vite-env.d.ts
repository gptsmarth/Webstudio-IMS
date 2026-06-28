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
  buildVersion: string;
  gitCommit: string;
  buildDate: string;
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

interface Window {
  api?: ApiNamespace;
  config?: ConfigNamespace;
  system?: SystemNamespace;
  storage?: StorageNamespace;
}
