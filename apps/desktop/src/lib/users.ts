import type { UserRole } from '../config/navigation';
import type {
  UserDetail,
  UserRole as ApiUserRole,
  UserStatus,
  UserSummary,
} from '../services/api/UserService';
import { formatRoleLabel } from '../store/useAuthStore';

export type UserSortField =
  | 'username'
  | 'display_name'
  | 'role'
  | 'status'
  | 'last_login_at'
  | 'created_at';

export const HUMAN_USER_ROLES: ApiUserRole[] = ['main_admin', 'admin', 'salesperson'];

import {
  canActivateUsers as canActivateUsersPermission,
  canCreateUsers as canCreateUsersPermission,
  canDeactivateUsers as canDeactivateUsersPermission,
  canEditUsers as canEditUsersPermission,
  canManageUsers as canManageUsersPermission,
  canResetUserPassword as canResetUserPasswordPermission,
} from '../services/PermissionService';

export function canManageUsers(permissions: string[]): boolean {
  return canManageUsersPermission(permissions);
}

export function canCreateUsers(permissions: string[]): boolean {
  return canCreateUsersPermission(permissions);
}

export function canEditUsers(permissions: string[]): boolean {
  return canEditUsersPermission(permissions);
}

export function canResetUserPassword(permissions: string[]): boolean {
  return canResetUserPasswordPermission(permissions);
}

export function canActivateUsers(permissions: string[]): boolean {
  return canActivateUsersPermission(permissions);
}

export function canDeactivateUsers(permissions: string[]): boolean {
  return canDeactivateUsersPermission(permissions);
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

export function userEffectiveStatus(user: {
  status: UserStatus;
  is_locked?: boolean;
  is_archived?: boolean;
}): { label: string; badgeClass: string } {
  if (user.is_archived) {
    return { label: 'Archived', badgeClass: 'usr-badge usr-badge--archived' };
  }
  if (user.is_locked) {
    return { label: 'Locked', badgeClass: 'usr-badge usr-badge--locked' };
  }
  return { label: userStatusLabel(user.status), badgeClass: userStatusBadgeClass(user.status) };
}

export function formatPasswordAge(days: number | null | undefined): string {
  if (days === null || days === undefined) return '—';
  if (days === 0) return 'Today';
  if (days === 1) return '1 day';
  return `${days} days`;
}

export function apiRoleLabel(role: ApiUserRole): string {
  return formatRoleLabel(role as UserRole);
}

export function canDisableUser(
  target: UserDetail | UserSummary,
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
  target: UserDetail | UserSummary,
  currentUserId: number | null,
  activeMainAdminCount: number,
): { allowed: boolean; reason?: string } {
  if (target.role === 'main_admin' && currentUserId === target.id && activeMainAdminCount <= 1) {
    return {
      allowed: false,
      reason: 'You cannot change role while you are the only Main Administrator.',
    };
  }
  if (target.role === 'main_admin' && activeMainAdminCount <= 1) {
    return { allowed: false, reason: 'Cannot change role of the last active Main Administrator.' };
  }
  return { allowed: true };
}

export function canEnableUser(target: UserDetail | UserSummary): boolean {
  return target.status === 'disabled' && !target.is_archived;
}

export function canArchiveUser(
  target: UserDetail | UserSummary,
  currentUserId: number | null,
  activeMainAdminCount: number,
): { allowed: boolean; reason?: string } {
  if (target.is_archived) {
    return { allowed: false, reason: 'User is already archived.' };
  }
  return canDisableUser(target, currentUserId, activeMainAdminCount);
}

export function canRestoreUser(target: UserDetail | UserSummary): boolean {
  return Boolean(target.is_archived);
}
