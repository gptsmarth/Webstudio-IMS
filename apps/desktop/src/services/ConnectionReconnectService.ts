import { ConfigService } from './ConfigService';
import { ConnectionDiagnosticsService } from './ConnectionDiagnosticsService';
import { SavedServerStore } from './SavedServerStore';
import { ApiClientProvider } from './api/ApiClientProvider';

/**
 * Refresh saved hostname/IP and reconnect without user action (M12D).
 */
export async function attemptAutomaticReconnect(): Promise<boolean> {
  const resolvedUrls = await SavedServerStore.resolveSavedUrls();
  const env = await ConfigService.getEnvironment();
  const candidates = [env.apiBaseUrl, ...resolvedUrls].filter(
    (url, index, list) => url && list.indexOf(url) === index,
  );

  for (const url of candidates) {
    try {
      const result = await ConnectionDiagnosticsService.testConnection(url);
      if (result.success) {
        await ConfigService.setApiBaseUrl(result.url);
        ApiClientProvider.reset();
        return true;
      }
    } catch {
      // Try next candidate.
    }
  }
  return false;
}
