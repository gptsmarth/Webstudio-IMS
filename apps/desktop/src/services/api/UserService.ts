import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export type UserRole = 'main_admin' | 'admin' | 'salesperson' | 'service_account';
export type UserStatus = 'active' | 'disabled';

export interface UserSummary {
  id: number;
  username: string;
  display_name: string | null;
  role: UserRole;
  status: UserStatus;
  must_change_password: boolean;
  theme_preference: string | null;
  last_login_at: string | null;
  created_at: string | null;
  failed_login_count: number;
  is_locked: boolean;
  is_archived: boolean;
  active_session_count: number;
  password_age_days: number | null;
  created_by_display_name: string | null;
}

export interface UserSessionSummary {
  id: number;
  device_label: string | null;
  ip_address: string | null;
  user_agent: string | null;
  remember_me: boolean;
  created_at: string;
  last_used_at: string | null;
  expires_at: string;
}

export interface UserLoginEventSummary {
  id: number;
  username: string;
  success: boolean;
  failure_reason: string | null;
  ip_address: string | null;
  device_label: string | null;
  created_at: string;
}

export interface UserDetail extends UserSummary {
  created_at: string;
  updated_at: string;
  permissions: string[];
  locked_until: string | null;
  password_changed_at: string | null;
  created_by_user_id: number | null;
  archived_at: string | null;
  sessions: UserSessionSummary[];
  login_events: UserLoginEventSummary[];
}

export interface RolePermissionsEntry {
  role: UserRole;
  permissions: string[];
}

export interface RolePermissionsResponse {
  roles: RolePermissionsEntry[];
}

export interface UsersListParams {
  status?: UserStatus;
  role?: UserRole;
  search?: string;
  created_from?: string;
  created_to?: string;
  sort_field?: string;
  sort_direction?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

export interface UsersListResult {
  items: UserSummary[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
}

export interface CreateUserRequest {
  username: string;
  display_name?: string | null;
  role: UserRole;
  temporary_password: string;
}

export interface UpdateUserRequest {
  display_name?: string | null;
}

export interface UpdateUserRoleRequest {
  role: UserRole;
}

export interface ResetPasswordRequest {
  temporary_password: string;
}

interface ListMeta {
  page?: number;
  page_size?: number;
  total_items?: number;
  total_pages?: number;
}

export class UserService {
  static async listUsers(params?: UsersListParams): Promise<UsersListResult> {
    LoggingService.debug('API', 'Fetching users list', params as unknown as Record<string, unknown>);
    const client = await ApiClientProvider.getClient();
    const response = await client.getRaw<UserSummary[], ListMeta>('/api/v1/users', {
      page: 1,
      page_size: 25,
      ...params,
    } as Record<string, unknown>);
    return {
      items: response.data,
      page: response.meta?.page ?? params?.page ?? 1,
      page_size: response.meta?.page_size ?? params?.page_size ?? 25,
      total_items: response.meta?.total_items ?? response.data.length,
      total_pages: response.meta?.total_pages ?? 1,
    };
  }

  static async getUser(userId: number): Promise<UserDetail> {
    LoggingService.debug('API', 'Fetching user detail', { userId });
    const client = await ApiClientProvider.getClient();
    return client.get<UserDetail>(`/api/v1/users/${userId}`);
  }

  static async createUser(payload: CreateUserRequest): Promise<UserDetail> {
    LoggingService.info('API', 'Creating user', { username: payload.username, role: payload.role });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>('/api/v1/users', payload);
  }

  static async updateUser(userId: number, payload: UpdateUserRequest): Promise<UserDetail> {
    LoggingService.info('API', 'Updating user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.patch<UserDetail>(`/api/v1/users/${userId}`, payload);
  }

  static async updateUserRole(userId: number, payload: UpdateUserRoleRequest): Promise<UserDetail> {
    LoggingService.info('API', 'Updating user role', { userId, role: payload.role });
    const client = await ApiClientProvider.getClient();
    return client.patch<UserDetail>(`/api/v1/users/${userId}/role`, payload);
  }

  static async resetPassword(userId: number, payload: ResetPasswordRequest): Promise<void> {
    LoggingService.info('API', 'Resetting user password', { userId });
    const client = await ApiClientProvider.getClient();
    await client.post(`/api/v1/users/${userId}/reset-password`, payload);
  }

  static async disableUser(userId: number): Promise<UserDetail> {
    LoggingService.info('API', 'Disabling user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>(`/api/v1/users/${userId}/disable`);
  }

  static async enableUser(userId: number): Promise<UserDetail> {
    LoggingService.info('API', 'Enabling user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>(`/api/v1/users/${userId}/enable`);
  }

  static async unlockUser(userId: number): Promise<UserDetail> {
    LoggingService.info('API', 'Unlocking user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>(`/api/v1/users/${userId}/unlock`);
  }

  static async forceLogoutUser(userId: number): Promise<{ success: boolean; sessions_revoked: number }> {
    LoggingService.info('API', 'Force logout user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<{ success: boolean; sessions_revoked: number }>(`/api/v1/users/${userId}/logout-all`);
  }

  static async archiveUser(userId: number): Promise<UserDetail> {
    LoggingService.info('API', 'Archiving user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>(`/api/v1/users/${userId}/archive`);
  }

  static async restoreUser(userId: number): Promise<UserDetail> {
    LoggingService.info('API', 'Restoring user', { userId });
    const client = await ApiClientProvider.getClient();
    return client.post<UserDetail>(`/api/v1/users/${userId}/restore`);
  }

  static async getRolePermissions(): Promise<RolePermissionsResponse> {
    LoggingService.debug('API', 'Fetching role permissions');
    const client = await ApiClientProvider.getClient();
    return client.get<RolePermissionsResponse>('/api/v1/users/role-permissions');
  }
}
