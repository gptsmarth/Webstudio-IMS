import type { DiscoveredServer } from '@webstudio/shared-kernel';

const DISCOVERY_TIMEOUT_MS = 4500;

export class NetworkDiscoveryService {
  static async discoverServers(timeoutMs = DISCOVERY_TIMEOUT_MS): Promise<DiscoveredServer[]> {
    if (!window.network?.startDiscovery) {
      return [];
    }
    await window.network.startDiscovery();
    await new Promise((resolve) => window.setTimeout(resolve, timeoutMs));
    const servers = await window.network.getDiscoveredServers();
    await window.network.stopDiscovery();
    return Array.isArray(servers) ? servers : [];
  }
}
