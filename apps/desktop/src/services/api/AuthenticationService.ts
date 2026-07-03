import { ApiClientProvider } from './ApiClientProvider';
import { triggerBlobDownload } from '../../lib/downloadBlob';
import { AuthTokenStore } from '../AuthTokenStore';
import { LoggingService } from '../LoggingService';
import type { AuthUserSummary } from '../../store/useAuthStore';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  session_id?: number;
  user: AuthUserSummary;
}

export interface CurrentUserResponse extends AuthUserSummary {
  permissions?: string[];
}

export interface ActiveSession {
  id: number;
  device_label: string | null;
  ip_address: string | null;
  user_agent: string | null;
  remember_me: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
  is_current: boolean;
}

export interface SecurityDashboard {
  session_timeout_minutes: number;
  active_session_count: number;
  active_sessions: ActiveSession[];
  locked_users: {
    id: number;
    username: string;
    display_name: string | null;
    locked_until: string | null;
    failed_login_count: number;
  }[];
  failed_logins_24h: number;
  password_policy: { rules: string[]; history_count: number };
  recovery: { configured: boolean; last_used_at: string | null };
  recent_login_events: {
    id: number;
    username: string;
    success: boolean;
    failure_reason: string | null;
    ip_address: string | null;
    device_label: string | null;
    created_at: string;
  }[];
  jwt_access_token_ttl_minutes: number;
  jwt_refresh_token_ttl_days: number;
  org_active_session_count: number;
  recent_security_events: {
    id: string;
    description: string | null;
    severity: string;
    security_event: string | null;
    actor_display_name: string | null;
    created_at: string;
  }[];
  critical_alerts: {
    id: string;
    description: string | null;
    severity: string;
    security_event: string | null;
    actor_display_name: string | null;
    created_at: string;
  }[];
}

export class AuthenticationService {
  static async login(credentials: {
    username: string;
    password: string;
    remember_me?: boolean;
    device_label?: string;
  }): Promise<LoginResponse> {
    LoggingService.info('API', 'Attempting user login');
    const client = await ApiClientProvider.getClient();
    const response = await client.post<LoginResponse>('/api/v1/auth/login', credentials);
    await AuthTokenStore.setTokens(
      response.access_token,
      response.refresh_token,
      response.expires_in,
    );
    if (response.session_id) {
      await AuthTokenStore.setSessionId(response.session_id);
    }
    return response;
  }

  static async refresh(): Promise<LoginResponse> {
    const refreshToken = await AuthTokenStore.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    const client = await ApiClientProvider.getClient();
    const response = await client.post<LoginResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    });
    await AuthTokenStore.setTokens(
      response.access_token,
      response.refresh_token,
      response.expires_in,
    );
    if (response.session_id) {
      await AuthTokenStore.setSessionId(response.session_id);
    }
    return response;
  }

  static async getCurrentUser(): Promise<CurrentUserResponse> {
    LoggingService.debug('API', 'Fetching current user profile');
    const client = await ApiClientProvider.getClient();
    return client.get<CurrentUserResponse>('/api/v1/auth/me');
  }

  static async listSessions(): Promise<ActiveSession[]> {
    const client = await ApiClientProvider.getClient();
    const refreshToken = await AuthTokenStore.getRefreshToken();
    return client.get<ActiveSession[]>('/api/v1/auth/sessions', {
      refresh_token: refreshToken ?? undefined,
    });
  }

  static async revokeSession(sessionId: number): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.delete(`/api/v1/auth/sessions/${sessionId}`);
  }

  static async logoutAll(): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.post('/api/v1/auth/logout-all');
    await AuthTokenStore.clear();
    ApiClientProvider.reset();
  }

  static async getSecurityDashboard(): Promise<SecurityDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<SecurityDashboard>('/api/v1/security/dashboard');
  }

  static async exportSecurityEvents(format: 'pdf' | 'xlsx'): Promise<void> {
    const client = await ApiClientProvider.getClient();
    const blob = await client.getBlob('/api/v1/security/export', { format });
    triggerBlobDownload(blob, `security-events.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
  }

  static async logout(): Promise<void> {
    LoggingService.info('API', 'Logging out user');
    const client = await ApiClientProvider.getClient();
    const refreshToken = await AuthTokenStore.getRefreshToken();
    try {
      if (refreshToken) {
        await client.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      }
    } finally {
      await AuthTokenStore.clear();
      ApiClientProvider.reset();
    }
  }

  static async restoreSession(): Promise<CurrentUserResponse | null> {
    const refreshToken = await AuthTokenStore.getRefreshToken();
    if (!refreshToken) return null;
    try {
      await AuthenticationService.refresh();
      return await AuthenticationService.getCurrentUser();
    } catch {
      await AuthTokenStore.clear();
      ApiClientProvider.reset();
      return null;
    }
  }
}
