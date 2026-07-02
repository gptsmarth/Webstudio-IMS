import Bonjour, { type Browser, type Service } from 'bonjour-service';

import {
  DISCOVERY_SERVICE_TYPE,
  type DiscoveredServer,
} from '@webstudio/shared-kernel';

const TXT_KEYS = {
  serverName: 'server_name',
  companyName: 'company_name',
  backendVersion: 'backend_version',
  apiVersion: 'api_version',
  buildVersion: 'build_version',
  environment: 'environment',
  backendPort: 'backend_port',
} as const;

function readTxt(service: Service, key: string): string {
  const raw = service.txt?.[key];
  if (Array.isArray(raw)) {
    return String(raw[0] ?? '').trim();
  }
  return String(raw ?? '').trim();
}

function toDiscoveredServer(service: Service): DiscoveredServer | null {
  const host = service.addresses?.find((address) => address.includes('.')) ?? service.host;
  if (!host) {
    return null;
  }
  const port = service.port || Number(readTxt(service, TXT_KEYS.backendPort)) || 8000;
  const serverName = readTxt(service, TXT_KEYS.serverName) || service.name.split('.')[0] || host;
  const companyName = readTxt(service, TXT_KEYS.companyName) || 'WEBSTUDIO';
  const id = `${service.name}-${host}-${port}`;
  return {
    id,
    serverName,
    companyName,
    backendVersion: readTxt(service, TXT_KEYS.backendVersion) || 'unknown',
    apiVersion: readTxt(service, TXT_KEYS.apiVersion) || '1.0',
    buildVersion: readTxt(service, TXT_KEYS.buildVersion) || '',
    environment: readTxt(service, TXT_KEYS.environment) || 'production',
    port,
    host,
    url: `http://${host}:${port}`,
    lastSeen: new Date().toISOString(),
    status: 'online',
  };
}

export class MdnsBrowser {
  private browser: Browser | null = null;
  private readonly servers = new Map<string, DiscoveredServer>();

  start(onUpdate: (servers: DiscoveredServer[]) => void): void {
    this.stop();
    this.servers.clear();
    const bonjour = new Bonjour();
    this.browser = bonjour.find({ type: 'webstudio-ims', protocol: 'tcp' });
    this.browser.on('up', (service: Service) => {
      const mapped = toDiscoveredServer(service);
      if (!mapped) return;
      this.servers.set(mapped.id, mapped);
      onUpdate(Array.from(this.servers.values()));
    });
    this.browser.on('down', (service: Service) => {
      const host = service.addresses?.[0] ?? service.host;
      const port = service.port || 8000;
      const idPrefix = `${service.name}-${host}-${port}`;
      for (const key of this.servers.keys()) {
        if (key.startsWith(idPrefix) || key.includes(service.name)) {
          this.servers.delete(key);
        }
      }
      onUpdate(Array.from(this.servers.values()));
    });
  }

  stop(): void {
    this.browser?.stop();
    this.browser = null;
    this.servers.clear();
  }
}

export { DISCOVERY_SERVICE_TYPE };
