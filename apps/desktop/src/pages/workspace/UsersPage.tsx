import { useMemo, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import { CataloguePagination } from '../../components/catalogue/CataloguePagination';
import {
  ChangeRoleDialog,
  ConfirmUserActionDialog,
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
import { canManageUsers } from '../../lib/users';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import type { UserDetail, UserSummary } from '../../services/api/UserService';
import { UserService } from '../../services/api/UserService';

export function UsersPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const workspace = useUsersWorkspace();

  const [createOpen, setCreateOpen] = useState(false);
  const [editUser, setEditUser] = useState<UserDetail | null>(null);
  const [resetUser, setResetUser] = useState<UserSummary | null>(null);
  const [roleUser, setRoleUser] = useState<UserSummary | null>(null);
  const [disableUser, setDisableUser] = useState<UserSummary | null>(null);
  const [enableUser, setEnableUser] = useState<UserSummary | null>(null);
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
          <h1 className="usr-page__title">Users</h1>
          <p className="usr-page__subtitle">Manage accounts, roles, and access for your organization.</p>
        </div>
      </header>

      <div className="usr-page__panel">
        <UsersToolbar workspace={workspace} onCreate={() => setCreateOpen(true)} />
        <UsersFiltersPanel
          filters={workspace.filters}
          setFilters={workspace.setFilters}
          resetFilters={workspace.resetFilters}
        />

        {workspace.error && (
          <div className="alert alert-danger usr-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.error}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => void workspace.refresh()}>
              Retry
            </button>
          </div>
        )}

        {workspace.actionError && (
          <div className="alert alert-danger usr-page__alert">
            <AlertCircle size={14} aria-hidden />
            <span>{workspace.actionError}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={workspace.clearActionError}>
              Dismiss
            </button>
          </div>
        )}

        <div className={`usr-page__body ${workspace.selectedId ? 'usr-page__body--drawer-open' : ''}`}>
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

      <ChangeRoleDialog
        open={Boolean(roleUser)}
        user={roleUser}
        rolePermissions={workspace.rolePermissions}
        loading={workspace.actionLoading}
        onClose={() => setRoleUser(null)}
        onConfirm={async (role) => {
          if (!roleUser) return;
          await workspace.changeRole(roleUser.id, role);
        }}
      />

      <ConfirmUserActionDialog
        open={Boolean(disableUser)}
        user={disableUser}
        title="Disable user"
        message="Disable access for"
        confirmLabel="Disable user"
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
        title="Enable user"
        message="Restore access for"
        confirmLabel="Enable user"
        loading={workspace.actionLoading}
        onClose={() => setEnableUser(null)}
        onConfirm={async () => {
          if (!enableUser) return;
          await workspace.enableUser(enableUser.id);
        }}
      />
    </div>
  );
}
