const ACCESS_TOKEN_KEY = 'webstudio_access_token';
const REFRESH_TOKEN_KEY = 'webstudio_refresh_token';
const ACCESS_EXPIRES_AT_KEY = 'webstudio_access_expires_at';
const SESSION_ID_KEY = 'webstudio_session_id';

async function readItem(key: string): Promise<string | null> {
  try {
    if (window.storage?.getItem) {
      const value = await window.storage.getItem(key);
      return typeof value === 'string' ? value : null;
    }
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

async function writeItem(key: string, value: string): Promise<void> {
  if (window.storage?.setItem) {
    await window.storage.setItem(key, value);
    return;
  }
  localStorage.setItem(key, value);
}

async function removeItem(key: string): Promise<void> {
  if (window.storage?.removeItem) {
    await window.storage.removeItem(key);
    return;
  }
  localStorage.removeItem(key);
}

export class AuthTokenStore {
  static async getAccessToken(): Promise<string | null> {
    return readItem(ACCESS_TOKEN_KEY);
  }

  static async getRefreshToken(): Promise<string | null> {
    return readItem(REFRESH_TOKEN_KEY);
  }

  static async getSessionId(): Promise<number | null> {
    const raw = await readItem(SESSION_ID_KEY);
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  }

  static async getAccessExpiresAt(): Promise<number | null> {
    const raw = await readItem(ACCESS_EXPIRES_AT_KEY);
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  }

  static async setTokens(accessToken: string, refreshToken: string, expiresInSeconds?: number): Promise<void> {
    await writeItem(ACCESS_TOKEN_KEY, accessToken);
    await writeItem(REFRESH_TOKEN_KEY, refreshToken);
    if (expiresInSeconds) {
      const expiresAt = Date.now() + expiresInSeconds * 1000;
      await writeItem(ACCESS_EXPIRES_AT_KEY, String(expiresAt));
    }
  }

  static async setSessionId(sessionId: number): Promise<void> {
    await writeItem(SESSION_ID_KEY, String(sessionId));
  }

  static async clear(): Promise<void> {
    await removeItem(ACCESS_TOKEN_KEY);
    await removeItem(REFRESH_TOKEN_KEY);
    await removeItem(ACCESS_EXPIRES_AT_KEY);
    await removeItem(SESSION_ID_KEY);
  }
}
