import { create } from 'zustand';
import type { UserRole } from '../config/navigation';

export interface AuthSession {
  id: number;
  username: string;
  displayName: string;
  role: UserRole;
  permissions: string[];
}

export interface AuthUserSummary {
  id?: number;
  username: string;
  display_name?: string | null;
  role: string;
  permissions?: string[];
}

interface AuthState {
  session: AuthSession | null;
  setSession: (session: AuthSession) => void;
  clearSession: () => void;
}

const API_ROLES: UserRole[] = ['main_admin', 'admin', 'salesperson'];

function normalizeRole(role: string): UserRole {
  const normalized = role.trim().toLowerCase() as UserRole;
  if (API_ROLES.includes(normalized)) {
    return normalized;
  }
  return 'salesperson';
}

export function sessionFromUser(user: AuthUserSummary): AuthSession {
  const username = user.username.trim();
  const displayName = user.display_name?.trim() || username;
  return {
    id: user.id ?? 0,
    username,
    displayName,
    role: normalizeRole(user.role),
    permissions: user.permissions ?? [],
  };
}

/** @deprecated Use sessionFromUser with login /auth/me response */
export function sessionFromUsername(username: string): AuthSession {
  const trimmed = username.trim();
  const normalized = trimmed.toLowerCase();
  let role: UserRole = 'salesperson';
  if (normalized.includes('main') || normalized === 'mainadmin') {
    role = 'main_admin';
  } else if (normalized.includes('admin')) {
    role = 'admin';
  }
  return {
    id: 0,
    username: trimmed,
    displayName: trimmed,
    role,
    permissions: [],
  };
}

export function formatRoleLabel(role: UserRole): string {
  switch (role) {
    case 'main_admin':
      return 'Main Administrator';
    case 'admin':
      return 'Administrator';
    case 'salesperson':
      return 'Salesperson';
    default:
      return role;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  setSession: (session) => set({ session }),
  clearSession: () => set({ session: null }),
}));
