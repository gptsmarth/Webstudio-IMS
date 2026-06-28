import type { UserRole } from '../config/navigation';
import type { UserDetail, UserRole as ApiUserRole, UserStatus } from '../services/api/UserService';
import { formatRoleLabel } from '../store/useAuthStore';

export type UserSortField =
  | 'username'
  | 'display_name'
  | 'role'
  | 'status'
  | 'last_login_at'
  | 'created_at';

export const HUMAN_USER_ROLES: ApiUserRole[] = ['main_admin', 'admin', 'salesperson'];

export function canManageUsers(permissions: string[]): boolean {
  return permissions.includes('users:manage');
}

export function userDisplayName(user: { username: string; display_name?: string | null }): string {
  return user.display_name?.trim() || user.username;
}

export function userInitials(user: { username: string; display_name?: string | null }): string {
  const label = userDisplayName(user);
  const parts = label.split(/\s+/).map((part) => part[0]?.toUpperCase() ?? '');
  const initials = parts.join('').slice(0, 2);
  return initials || user.username.slice(0, 2).toUpperCase();
}

export function userStatusLabel(status: UserStatus): string {
  return status === 'active' ? 'Active' : 'Disabled';
}

export function userStatusBadgeClass(status: UserStatus): string {
  return status === 'active' ? 'usr-badge usr-badge--active' : 'usr-badge usr-badge--disabled';
}

export function apiRoleLabel(role: ApiUserRole): string {
  return formatRoleLabel(role as UserRole);
}

export function canDisableUser(
  target: UserDetail,
  currentUserId: number | null,
  activeMainAdminCount: number,
): { allowed: boolean; reason?: string } {
  if (target.status === 'disabled') {
    return { allowed: false, reason: 'User is already disabled.' };
  }
  if (target.role === 'main_admin' && currentUserId === target.id) {
    return { allowed: false, reason: 'You cannot disable your own Main Administrator account.' };
  }
  if (target.role === 'main_admin' && activeMainAdminCount <= 1) {
    return { allowed: false, reason: 'Cannot disable the last active Main Administrator.' };
  }
  return { allowed: true };
}

export function canChangeRole(
  target: UserDetail,
  currentUserId: number | null,
  activeMainAdminCount: number,
): { allowed: boolean; reason?: string } {
  if (target.role === 'main_admin' && currentUserId === target.id && activeMainAdminCount <= 1) {
    return { allowed: false, reason: 'You cannot change role while you are the only Main Administrator.' };
  }
  if (target.role === 'main_admin' && activeMainAdminCount <= 1) {
    return { allowed: false, reason: 'Cannot change role of the last active Main Administrator.' };
  }
  return { allowed: true };
}

export function canEnableUser(target: UserDetail): boolean {
  return target.status === 'disabled';
}
