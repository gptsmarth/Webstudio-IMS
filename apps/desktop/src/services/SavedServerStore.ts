import {
  buildServerUrl,
  extractHostnameFromUrl,
  normalizeServerUrl,
  type SavedServerRecord,
} from '@webstudio/shared-kernel';

const SAVED_SERVERS_KEY = 'webstudio_saved_servers';

export class SavedServerStore {
  static async list(): Promise<SavedServerRecord[]> {
    const raw = await window.storage?.getItem(SAVED_SERVERS_KEY);
    if (!Array.isArray(raw)) {
      return [];
    }
    return raw.filter((entry): entry is SavedServerRecord => typeof entry?.url === 'string');
  }

  static async save(record: SavedServerRecord): Promise<void> {
    const normalizedUrl = normalizeServerUrl(record.url);
    const hostname = record.hostname ?? extractHostnameFromUrl(normalizedUrl);
    const updated: SavedServerRecord = {
      ...record,
      url: normalizedUrl,
      hostname,
      lastConnectedAt: record.lastConnectedAt ?? new Date().toISOString(),
      lastSeenAt: new Date().toISOString(),
    };
    const existing = await this.list();
    const merged = [updated, ...existing.filter((entry) => entry.url !== normalizedUrl)].slice(
      0,
      8,
    );
    await window.storage?.setItem(SAVED_SERVERS_KEY, merged);
  }

  static async remove(url: string): Promise<void> {
    const normalizedUrl = normalizeServerUrl(url);
    const updated = (await this.list()).filter((entry) => entry.url !== normalizedUrl);
    await window.storage?.setItem(SAVED_SERVERS_KEY, updated);
  }

  static async resolveSavedUrls(): Promise<string[]> {
    const servers = await this.list();
    const urls: string[] = [];
    for (const server of servers) {
      const parsedPort = Number(new URL(server.url).port || 8000);
      if (server.hostname && window.network?.resolveHost) {
        try {
          const resolved = await window.network.resolveHost(server.hostname);
          if (resolved.resolved && resolved.resolvedIp) {
            const refreshed = buildServerUrl(server.hostname, parsedPort);
            await this.save({
              ...server,
              url: refreshed,
              currentIp: resolved.resolvedIp,
              lastSeenAt: new Date().toISOString(),
            });
            urls.push(refreshed);
            continue;
          }
        } catch {
          // Fall back to stored URL.
        }
      }
      urls.push(server.url);
    }
    return urls;
  }
}
