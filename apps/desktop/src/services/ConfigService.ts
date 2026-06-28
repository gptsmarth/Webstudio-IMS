export type AppMode = 'development' | 'production' | 'test';

export interface AppEnvironment {
  mode: AppMode;
  apiBaseUrl: string;
  isOfflineMode: boolean;
}

export class ConfigService {
  private static cachedEnv: AppEnvironment | null = null;

  static async getEnvironment(): Promise<AppEnvironment> {
    if (this.cachedEnv) {
      return this.cachedEnv;
    }

    let mode: AppMode = 'development';
    let apiBaseUrl = 'http://127.0.0.1:8000';

    try {
      if (typeof window !== 'undefined' && window.config?.getEnv) {
        const env = await window.config.getEnv();
        mode = env.mode;
        apiBaseUrl = env.apiBaseUrl;
      } else {
        const rawMode = import.meta.env.MODE;
        if (rawMode === 'production' || rawMode === 'test') {
          mode = rawMode;
        }
        apiBaseUrl = import.meta.env.VITE_API_BASE_URL || apiBaseUrl;
      }
    } catch {
      // Fallback to default dev settings
    }

    this.cachedEnv = {
      mode,
      apiBaseUrl: apiBaseUrl.replace(/\/$/, ''),
      isOfflineMode: false,
    };

    return this.cachedEnv;
  }

  static async setApiBaseUrl(url: string): Promise<void> {
    if (this.cachedEnv) {
      this.cachedEnv.apiBaseUrl = url.replace(/\/$/, '');
    }
    try {
      if (typeof window !== 'undefined' && window.config?.set) {
        await window.config.set('apiBaseUrl', url);
      } else {
        localStorage.setItem('webstudio_api_url', url);
      }
    } catch {
      // Ignore save error
    }
  }
}
