import { ApiClientProvider } from './ApiClientProvider';
import { AuthTokenStore } from '../AuthTokenStore';
import { LoggingService } from '../LoggingService';
import type { AuthUserSummary } from '../../store/useAuthStore';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUserSummary;
}

export interface CurrentUserResponse extends AuthUserSummary {
  permissions?: string[];
}

export class AuthenticationService {
  static async login(credentials: Record<string, string>): Promise<LoginResponse> {
    LoggingService.info('API', 'Attempting user login');
    const client = await ApiClientProvider.getClient();
    const response = await client.post<LoginResponse>('/api/v1/auth/login', credentials);
    await AuthTokenStore.setTokens(response.access_token, response.refresh_token);
    return response;
  }

  static async getCurrentUser(): Promise<CurrentUserResponse> {
    LoggingService.debug('API', 'Fetching current user profile');
    const client = await ApiClientProvider.getClient();
    return client.get<CurrentUserResponse>('/api/v1/auth/me');
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
}
