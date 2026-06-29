import { useCallback, useEffect, useState } from 'react';
import { useDebounce } from '../lib/useDebounce';
import type { UserSortField } from '../lib/users';
import { AuditService, type AuditLogEntry } from '../services/api/AuditService';
import {
  UserService,
  type RolePermissionsEntry,
  type UserDetail,
  type UserRole,
  type UserStatus,
  type UserSummary,
} from '../services/api/UserService';

export interface UsersFilters {
  role: UserRole | '';
  status: UserStatus | '';
  createdFrom: string;
  createdTo: string;
}

export const DEFAULT_USERS_FILTERS: UsersFilters = {
  role: '',
  status: '',
  createdFrom: '',
  createdTo: '',
};

export interface UsersWorkspaceState {
  items: UserSummary[];
  loading: boolean;
  error: string | null;
  search: string;
  setSearch: (value: string) => void;
  filters: UsersFilters;
  setFilters: (patch: Partial<UsersFilters>) => void;
  resetFilters: () => void;
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  setPage: (page: number) => void;
  sortField: UserSortField;
  sortDirection: 'asc' | 'desc';
  toggleSort: (field: UserSortField) => void;
  selectedId: number | null;
  selectedUser: UserDetail | null;
  selectUser: (id: number | null) => void;
  auditLogs: AuditLogEntry[];
  rolePermissions: RolePermissionsEntry[];
  drawerLoading: boolean;
  actionLoading: boolean;
  actionError: string | null;
  clearActionError: () => void;
  activeMainAdminCount: number;
  refresh: () => Promise<void>;
  createUser: (payload: {
    username: string;
    display_name?: string | null;
    role: UserRole;
    temporary_password: string;
  }) => Promise<UserDetail>;
  updateUser: (userId: number, displayName: string) => Promise<UserDetail>;
  changeRole: (userId: number, role: UserRole) => Promise<UserDetail>;
  resetPassword: (userId: number, temporaryPassword: string) => Promise<void>;
  disableUser: (userId: number) => Promise<UserDetail>;
  enableUser: (userId: number) => Promise<UserDetail>;
  unlockUser: (userId: number) => Promise<UserDetail>;
  forceLogoutUser: (userId: number) => Promise<number>;
  archiveUser: (userId: number) => Promise<UserDetail>;
  restoreUser: (userId: number) => Promise<UserDetail>;
}

export function useUsersWorkspace(): UsersWorkspaceState {
  const [items, setItems] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [filters, setFiltersState] = useState<UsersFilters>(DEFAULT_USERS_FILTERS);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [sortField, setSortField] = useState<UserSortField>('username');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedUser, setSelectedUser] = useState<UserDetail | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [rolePermissions, setRolePermissions] = useState<RolePermissionsEntry[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [activeMainAdminCount, setActiveMainAdminCount] = useState(0);

  const debouncedSearch = useDebounce(search, 300);

  const setFilters = useCallback((patch: Partial<UsersFilters>) => {
    setFiltersState((current) => ({ ...current, ...patch }));
    setPage(1);
  }, []);

  const resetFilters = useCallback(() => {
    setFiltersState(DEFAULT_USERS_FILTERS);
    setPage(1);
  }, []);

  const toggleSort = useCallback((field: UserSortField) => {
    setSortField((current) => {
      if (current === field) {
        setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
        return current;
      }
      setSortDirection('asc');
      return field;
    });
    setPage(1);
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await UserService.listUsers({
        page,
        page_size: pageSize,
        search: debouncedSearch.trim() || undefined,
        role: filters.role || undefined,
        status: filters.status || undefined,
        created_from: filters.createdFrom || undefined,
        created_to: filters.createdTo || undefined,
        sort_field: sortField,
        sort_direction: sortDirection,
      });
      setItems(result.items);
      setTotalItems(result.total_items);
      setTotalPages(result.total_pages);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load users.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, debouncedSearch, filters, sortField, sortDirection]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    void (async () => {
      try {
        const result = await UserService.listUsers({
          role: 'main_admin',
          status: 'active',
          page: 1,
          page_size: 1,
        });
        setActiveMainAdminCount(result.total_items);
      } catch {
        setActiveMainAdminCount(0);
      }
    })();
  }, [items]);

  useEffect(() => {
    void (async () => {
      try {
        const response = await UserService.getRolePermissions();
        setRolePermissions(response.roles);
      } catch {
        setRolePermissions([]);
      }
    })();
  }, []);

  const selectUser = useCallback((id: number | null) => {
    setSelectedId(id);
    if (!id) {
      setSelectedUser(null);
      setAuditLogs([]);
    }
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    let cancelled = false;
    setDrawerLoading(true);
    void (async () => {
      try {
        const [detail, entityAudits, actorAudits] = await Promise.all([
          UserService.getUser(selectedId),
          AuditService.listLogs({ entity_type: 'user', entity_id: String(selectedId), page_size: 20 }),
          AuditService.listLogs({ actor_user_id: selectedId, page_size: 20 }),
        ]);
        if (cancelled) return;
        setSelectedUser(detail);
        const merged = [...entityAudits.items, ...actorAudits.items]
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .filter((log, index, array) => array.findIndex((row) => row.id === log.id) === index)
          .slice(0, 15);
        setAuditLogs(merged);
      } catch (err: unknown) {
        if (cancelled) return;
        const message = err as { message?: string };
        setActionError(message.message ?? 'Unable to load user details.');
      } finally {
        if (!cancelled) setDrawerLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const runAction = useCallback(async <T,>(action: () => Promise<T>): Promise<T> => {
    setActionLoading(true);
    setActionError(null);
    try {
      return await action();
    } catch (err: unknown) {
      const message = err as { message?: string; detail?: string };
      setActionError(message.message ?? message.detail ?? 'Action failed.');
      throw err;
    } finally {
      setActionLoading(false);
    }
  }, []);

  const createUser = useCallback(
    async (payload: {
      username: string;
      display_name?: string | null;
      role: UserRole;
      temporary_password: string;
    }) => {
      const created = await runAction(() => UserService.createUser(payload));
      await refresh();
      return created;
    },
    [refresh, runAction],
  );

  const updateUser = useCallback(
    async (userId: number, displayName: string) => {
      const updated = await runAction(() => UserService.updateUser(userId, { display_name: displayName }));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const changeRole = useCallback(
    async (userId: number, role: UserRole) => {
      const updated = await runAction(() => UserService.updateUserRole(userId, { role }));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const resetPassword = useCallback(
    async (userId: number, temporaryPassword: string) => {
      await runAction(() => UserService.resetPassword(userId, { temporary_password: temporaryPassword }));
    },
    [runAction],
  );

  const disableUser = useCallback(
    async (userId: number) => {
      const updated = await runAction(() => UserService.disableUser(userId));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const enableUser = useCallback(
    async (userId: number) => {
      const updated = await runAction(() => UserService.enableUser(userId));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const unlockUser = useCallback(
    async (userId: number) => {
      const updated = await runAction(() => UserService.unlockUser(userId));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const forceLogoutUser = useCallback(
    async (userId: number) => {
      const result = await runAction(() => UserService.forceLogoutUser(userId));
      await refresh();
      if (selectedId === userId) {
        const detail = await UserService.getUser(userId);
        setSelectedUser(detail);
      }
      return result.sessions_revoked;
    },
    [refresh, runAction, selectedId],
  );

  const archiveUser = useCallback(
    async (userId: number) => {
      const updated = await runAction(() => UserService.archiveUser(userId));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  const restoreUser = useCallback(
    async (userId: number) => {
      const updated = await runAction(() => UserService.restoreUser(userId));
      await refresh();
      if (selectedId === userId) setSelectedUser(updated);
      return updated;
    },
    [refresh, runAction, selectedId],
  );

  return {
    items,
    loading,
    error,
    search,
    setSearch,
    filters,
    setFilters,
    resetFilters,
    page,
    pageSize,
    totalItems,
    totalPages,
    setPage,
    sortField,
    sortDirection,
    toggleSort,
    selectedId,
    selectedUser,
    selectUser,
    auditLogs,
    rolePermissions,
    drawerLoading,
    actionLoading,
    actionError,
    clearActionError: () => setActionError(null),
    activeMainAdminCount,
    refresh,
    createUser,
    updateUser,
    changeRole,
    resetPassword,
    disableUser,
    enableUser,
    unlockUser,
    forceLogoutUser,
    archiveUser,
    restoreUser,
  };
}
