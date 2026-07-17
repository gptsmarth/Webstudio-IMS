import { normalizeServerUrl, type ConnectionDiagnosticsResult } from '@webstudio/shared-kernel';
import { ConfigService } from './ConfigService';
import { ConnectionDiagnosticsService } from './ConnectionDiagnosticsService';
import { NetworkDiscoveryService } from './NetworkDiscoveryService';
import { SavedServerStore } from './SavedServerStore';
import { ApiClientProvider } from './api/ApiClientProvider';

/** Static LAN probes when mDNS is unavailable (office Wi‑Fi / AP isolation). */
export const LAN_DISCOVERY_CANDIDATE_URLS = [
  'http://127.0.0.1:8000',
  'http://localhost:8000',
  'http://192.168.29.100:8000',
  'http://192.168.1.100:8000',
  'http://192.168.0.100:8000',
  'http://192.168.1.1:8000',
];

/**
 * Discover and validate a WEBSTUDIO server on the LAN.
 * Order: preferred/saved URLs → mDNS → static shop candidates.
 */
export async function discoverBestServer(options?: {
  preferredUrl?: string;
  includeMdns?: boolean;
}): Promise<ConnectionDiagnosticsResult | null> {
  const includeMdns = options?.includeMdns !== false;
  const resolvedUrls = await SavedServerStore.resolveSavedUrls();
  const preferred = options?.preferredUrl?.trim()
    ? [normalizeServerUrl(options.preferredUrl.trim())]
    : [];

  const earlyCandidates = [...new Set([...preferred, ...resolvedUrls])].filter(Boolean);
  for (const url of earlyCandidates) {
    try {
      const result = await ConnectionDiagnosticsService.testConnection(url);
      if (result.success) {
        return result;
      }
    } catch {
      // Try next.
    }
  }

  if (includeMdns) {
    try {
      const mdnsServers = await NetworkDiscoveryService.discoverServers();
      for (const server of mdnsServers) {
        try {
          const result = await ConnectionDiagnosticsService.testConnection(server.url);
          if (result.success) {
            return result;
          }
        } catch {
          // Try next discovered host.
        }
      }
    } catch {
      // Fall through to static probes.
    }
  }

  for (const url of LAN_DISCOVERY_CANDIDATE_URLS) {
    if (earlyCandidates.includes(url)) continue;
    try {
      const result = await ConnectionDiagnosticsService.testConnection(url);
      if (result.success) {
        return result;
      }
    } catch {
      // Try next candidate.
    }
  }

  return null;
}

/** @deprecated Prefer discoverBestServer — kept for callers that only need a URL. */
export async function discoverBestServerUrl(options?: {
  preferredUrl?: string;
  includeMdns?: boolean;
}): Promise<string | null> {
  const result = await discoverBestServer(options);
  return result?.url ?? null;
}

/**
 * Refresh saved hostname/IP and reconnect without user action (M12D).
 * Also runs mDNS + static LAN probes so Wi‑Fi clients find the server automatically.
 */
export async function attemptAutomaticReconnect(): Promise<boolean> {
  const env = await ConfigService.getEnvironment();
  const result = await discoverBestServer({ preferredUrl: env.apiBaseUrl });
  if (!result?.success) {
    return false;
  }

  await ConfigService.setApiBaseUrl(result.url);
  await SavedServerStore.save({
    url: result.url,
    companyName: result.companyName,
    friendlyName: result.companyName,
    backendVersion: result.backendVersion,
    hostname: result.url ? new URL(result.url).hostname : undefined,
    lastConnectedAt: new Date().toISOString(),
  });
  ApiClientProvider.reset();
  return true;
}
