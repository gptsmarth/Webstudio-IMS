import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface CustomAccessRoleSummary {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  permission_count: number;
  assigned_user_count: number;
}

export interface CustomAccessRoleDetail extends CustomAccessRoleSummary {
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface AssignUserAccessRequest {
  access_type: 'builtin' | 'custom';
  role?: string;
  custom_role_id?: number | null;
}

export class AccessRoleService {
  static async listCatalog(): Promise<string[]> {
    const client = await ApiClientProvider.getClient();
    const response = await client.get<{ permissions: string[] }>('/api/v1/access-roles/catalog');
    return response.permissions;
  }

  static async listRoles(includeInactive = false): Promise<CustomAccessRoleSummary[]> {
    const client = await ApiClientProvider.getClient();
    return client.get<CustomAccessRoleSummary[]>('/api/v1/access-roles', {
      include_inactive: includeInactive,
    });
  }

  static async getRole(roleId: number): Promise<CustomAccessRoleDetail> {
    const client = await ApiClientProvider.getClient();
    return client.get<CustomAccessRoleDetail>(`/api/v1/access-roles/${roleId}`);
  }

  static async createRole(payload: {
    name: string;
    description?: string | null;
    permissions: string[];
  }): Promise<CustomAccessRoleDetail> {
    LoggingService.debug('API', 'Creating custom access role', { name: payload.name });
    const client = await ApiClientProvider.getClient();
    return client.post<CustomAccessRoleDetail>('/api/v1/access-roles', payload);
  }

  static async updateRole(
    roleId: number,
    payload: {
      name?: string;
      description?: string | null;
      permissions?: string[];
      is_active?: boolean;
    },
  ): Promise<CustomAccessRoleDetail> {
    const client = await ApiClientProvider.getClient();
    return client.patch<CustomAccessRoleDetail>(`/api/v1/access-roles/${roleId}`, payload);
  }

  static async deleteRole(roleId: number): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.delete(`/api/v1/access-roles/${roleId}`);
  }

  static async assignUserAccess(userId: number, payload: AssignUserAccessRequest): Promise<void> {
    const client = await ApiClientProvider.getClient();
    await client.patch(`/api/v1/users/${userId}/access`, payload);
  }
}
