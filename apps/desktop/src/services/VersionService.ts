export class VersionService {
  static async getVersionInfo(): Promise<VersionInfo> {
    try {
      if (typeof window !== 'undefined' && window.system?.getVersionInfo) {
        return await window.system.getVersionInfo();
      }
    } catch {
      // Ignore IPC error and return fallback
    }

    return {
      appVersion: '0.1.0',
      buildNumber: 1,
      buildVersion: '0.1.0-web-fallback',
      gitCommit: import.meta.env.MODE === 'development' ? 'dev-local' : 'unknown',
      buildDate: new Date().toISOString().split('T')[0],
      releaseChannel: 'development',
      electronVersion: 'web-browser',
      chromiumVersion: 'web-browser',
      nodeVersion: 'web-browser',
    };
  }
}
