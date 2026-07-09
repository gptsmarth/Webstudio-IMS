import { useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { CataloguePagination } from '../../components/catalogue/CataloguePagination';
import {
  ChangeAccessDialog,
  ConfirmUserActionDialog,
  CustomRolesPanel,
  ResetPasswordDialog,
  UserDetailDrawer,
  UserFormDialog,
  UserRowActionsMenu,
  type UserRowAction,
  UsersFiltersPanel,
  UsersTable,
  UsersToolbar,
} from '../../components/users';
import { useUsersWorkspace } from '../../hooks/useUsersWorkspace';
import { canCreateUsers, canManageUsers } from '../../lib/users';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import type { UserDetail, UserSummary } from '../../services/api/UserService';
import { UserService } from '../../services/api/UserService';

export function UsersPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const workspace = useUsersWorkspace(session?.permissions ?? []);

  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<UserDetail | null>(null);
  const [resetUser, setResetUser] = useState<UserSummary | null>(null);
  const [roleUser, setRoleUser] = useState<UserSummary | null>(null);
  const [disableUser, setDisableUser] = useState<UserSummary | null>(null);
  const [enableUser, setEnableUser] = useState<UserSummary | null>(null);
  const [unlockUser, setUnlockUser] = useState<UserSummary | null>(null);
  const [forceLogoutUser, setForceLogoutUser] = useState<UserSummary | null>(null);
  const [archiveUser, setArchiveUser] = useState<UserSummary | null>(null);
  const [restoreUser, setRestoreUser] = useState<UserSummary | null>(null);
  const [menu, setMenu] = useState<{ user: UserSummary; rect: DOMRect } | null>(null);

  const openEdit = async (user: UserSummary) => {
    const detail = await UserService.getUser(user.id);
    setEditUser(detail);
  };

  const handleMenuAction = async (action: UserRowAction) => {
    if (!menu) return;
    const { user } = menu;
    setMenu(null);
    if (action === 'view') workspace.selectUser(user.id);
    else if (action === 'edit') await openEdit(user);
    else if (action === 'reset-password') setResetUser(user);
    else if (action === 'change-role') setRoleUser(user);
    else if (action === 'disable') setDisableUser(user);
    else if (action === 'enable') setEnableUser(user);
    else if (action === 'unlock') setUnlockUser(user);
    else if (action === 'force-logout') setForceLogoutUser(user);
    else if (action === 'archive') setArchiveUser(user);
    else if (action === 'restore') setRestoreUser(user);
  };

  const permissionDenied = useMemo(() => {
    if (!session) return 'Sign in again to access user administration.';
    if (!canManageUsers(session.permissions)) {
      return 'Your account does not have permission to manage users.';
    }
    return null;
  }, [session]);

  if (permissionDenied) {
    return (
      <div className="usr-page">
        <div className="usr-empty">
          <p className="usr-empty__title">Access restricted</p>
          <p className="usr-empty__text">{permissionDenied}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="usr-page animate-fade-in">
      <header className="usr-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="usr-page__title">Administration</h1>
          <p className="usr-page__subtitle">
            User accounts, access control, sessions, and security operations.
          </p>
        </div>
      </header>

      <div className="usr-page__panel">
        {session.role === 'main_admin' && (
          <CustomRolesPanel onRolesChanged={() => void workspace.refresh()} />
        )}

        <UsersToolbar
          workspace={workspace}
          onCreate={() => setCreateOpen(true)}
          canCreate={session ? canCreateUsers(session.permissions) : false}
        />
        <UsersFiltersPanel
          filters={workspace.filters}
          setFilters={workspace.setFilters}
          resetFilters={workspace.resetFilters}
        />

        {workspace.error && (
          <div className="alert alert-danger usr-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.error}</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => void workspace.refresh()}
            >
              Retry
            </button>
          </div>
        )}

        {workspace.actionError && (
          <div className="alert alert-danger usr-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.actionError}</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={workspace.clearActionError}
            >
              Dismiss
            </button>
          </div>
        )}

        <div
          className={`usr-page__body ${workspace.selectedId ? 'usr-page__body--drawer-open' : ''}`}
        >
          <UsersTable
            workspace={workspace}
            currentUserId={session?.id ?? null}
            onView={(user) => workspace.selectUser(user.id)}
            onMenu={(user, rect) => setMenu({ user, rect })}
          />
          <UserDetailDrawer workspace={workspace} />
        </div>

        <CataloguePagination
          page={workspace.page}
          pageSize={workspace.pageSize}
          totalItems={workspace.totalItems}
          onPageChange={workspace.setPage}
          loading={workspace.loading}
        />
      </div>

      {menu && (
        <UserRowActionsMenu
          user={menu.user}
          anchorRect={menu.rect}
          currentUserId={session?.id ?? null}
          activeMainAdminCount={workspace.activeMainAdminCount}
          permissions={session?.permissions ?? []}
          onAction={(action) => void handleMenuAction(action)}
          onClose={() => setMenu(null)}
        />
      )}

      <UserFormDialog
        open={createOpen}
        user={null}
        loading={workspace.actionLoading}
        onClose={() => setCreateOpen(false)}
        onCreate={async (payload) => {
          await workspace.createUser(payload);
        }}
        onUpdate={async () => {}}
      />

      <UserFormDialog
        open={Boolean(editUser)}
        user={editUser}
        loading={workspace.actionLoading}
        onClose={() => setEditUser(null)}
        onCreate={async () => {}}
        onUpdate={async (displayName) => {
          if (!editUser) return;
          await workspace.updateUser(editUser.id, displayName);
        }}
      />

      <ResetPasswordDialog
        open={Boolean(resetUser)}
        user={resetUser}
        loading={workspace.actionLoading}
        onClose={() => setResetUser(null)}
        onConfirm={async (password) => {
          if (!resetUser) return;
          await workspace.resetPassword(resetUser.id, password);
        }}
      />

      <ChangeAccessDialog
        open={Boolean(roleUser)}
        user={roleUser}
        rolePermissions={workspace.rolePermissions}
        loading={workspace.actionLoading}
        onClose={() => setRoleUser(null)}
        onConfirmBuiltin={async (role) => {
          if (!roleUser) return;
          await workspace.assignBuiltinAccess(roleUser.id, role);
        }}
        onConfirmCustom={async (customRoleId) => {
          if (!roleUser) return;
          await workspace.assignCustomAccess(roleUser.id, customRoleId);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(disableUser)}
        user={disableUser}
        title="Deactivate user"
        message="Deactivate access for"
        confirmLabel="Deactivate user"
        danger
        loading={workspace.actionLoading}
        onClose={() => setDisableUser(null)}
        onConfirm={async () => {
          if (!disableUser) return;
          await workspace.disableUser(disableUser.id);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(enableUser)}
        user={enableUser}
        title="Activate user"
        message="Restore access for"
        confirmLabel="Activate user"
        loading={workspace.actionLoading}
        onClose={() => setEnableUser(null)}
        onConfirm={async () => {
          if (!enableUser) return;
          await workspace.enableUser(enableUser.id);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(unlockUser)}
        user={unlockUser}
        title="Unlock user"
        message="Clear lockout for"
        confirmLabel="Unlock user"
        loading={workspace.actionLoading}
        onClose={() => setUnlockUser(null)}
        onConfirm={async () => {
          if (!unlockUser) return;
          await workspace.unlockUser(unlockUser.id);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(forceLogoutUser)}
        user={forceLogoutUser}
        title="Force logout"
        message="Revoke all active sessions for"
        confirmLabel="Force logout"
        danger
        loading={workspace.actionLoading}
        onClose={() => setForceLogoutUser(null)}
        onConfirm={async () => {
          if (!forceLogoutUser) return;
          await workspace.forceLogoutUser(forceLogoutUser.id);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(archiveUser)}
        user={archiveUser}
        title="Archive user"
        message="Archive account for"
        confirmLabel="Archive user"
        danger
        loading={workspace.actionLoading}
        onClose={() => setArchiveUser(null)}
        onConfirm={async () => {
          if (!archiveUser) return;
          await workspace.archiveUser(archiveUser.id);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(restoreUser)}
        user={restoreUser}
        title="Restore user"
        message="Restore archived account for"
        confirmLabel="Restore user"
        loading={workspace.actionLoading}
        onClose={() => setRestoreUser(null)}
        onConfirm={async () => {
          if (!restoreUser) return;
          await workspace.restoreUser(restoreUser.id);
        }}
      />
    </div>
  );
}
