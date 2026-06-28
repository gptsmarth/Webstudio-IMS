import { X } from 'lucide-react';
import { formatDateTime, formatRelativeTime } from '../../lib/datetime';
import type { UsersWorkspaceState } from '../../hooks/useUsersWorkspace';
import { apiRoleLabel, userDisplayName, userStatusBadgeClass, userStatusLabel } from '../../lib/users';
import type { AuditLogEntry } from '../../services/api/AuditService';
import { PermissionViewer } from './PermissionViewer';
import { UserAvatar } from './UserAvatar';

interface UserDetailDrawerProps {
  workspace: Pick<
    UsersWorkspaceState,
    'selectedId' | 'selectedUser' | 'selectUser' | 'auditLogs' | 'rolePermissions' | 'drawerLoading'
  >;
}

function AuditRow({ log }: { log: AuditLogEntry }): JSX.Element {
  return (
    <li className="usr-audit-row">
      <span className="usr-audit-row__action">{log.action.replaceAll('_', ' ')}</span>
      <span className="usr-audit-row__meta">
        {formatDateTime(log.created_at)}
        {log.actor_display_name ? ` · ${log.actor_display_name}` : ''}
      </span>
      {log.description && <span className="usr-audit-row__desc">{log.description}</span>}
    </li>
  );
}

export function UserDetailDrawer({ workspace }: UserDetailDrawerProps): JSX.Element | null {
  const user = workspace.selectedUser;
  if (!workspace.selectedId) return null;

  return (
    <aside className="usr-drawer animate-slide-in" aria-label="User details">
      <header className="usr-drawer__header">
        <div className="usr-drawer__identity">
          {user && <UserAvatar user={user} size="md" />}
          <div>
            <p className="usr-drawer__eyebrow">User account</p>
            <h2 className="usr-drawer__title">{user ? userDisplayName(user) : 'Loading…'}</h2>
            {user && <p className="usr-drawer__username col-mono">@{user.username}</p>}
          </div>
        </div>
        <button
          type="button"
          className="app-toolbar-icon-btn"
          onClick={() => workspace.selectUser(null)}
          aria-label="Close drawer"
        >
          <X size={16} aria-hidden />
        </button>
      </header>

      {workspace.drawerLoading && <p className="usr-drawer__loading">Loading user details…</p>}

      {user && !workspace.drawerLoading && (
        <div className="usr-drawer__body">
          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Basic information</h3>
            <dl className="usr-drawer__dl">
              <div>
                <dt>Full name</dt>
                <dd>{userDisplayName(user)}</dd>
              </div>
              <div>
                <dt>Username</dt>
                <dd className="col-mono">{user.username}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd className="usr-drawer__muted">Not configured</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>
                  <span className={userStatusBadgeClass(user.status)}>{userStatusLabel(user.status)}</span>
                </dd>
              </div>
              <div>
                <dt>Assigned store</dt>
                <dd className="usr-drawer__muted">Not assigned</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatDateTime(user.created_at)}</dd>
              </div>
            </dl>
          </section>

          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Role</h3>
            <p className="usr-drawer__role">{apiRoleLabel(user.role)}</p>
          </section>

          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Permissions</h3>
            <PermissionViewer rolePermissions={workspace.rolePermissions} selectedRole={user.role} compact />
          </section>

          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Recent login</h3>
            <p>{user.last_login_at ? formatDateTime(user.last_login_at) : 'Never logged in'}</p>
            {user.last_login_at && (
              <p className="usr-drawer__muted">{formatRelativeTime(user.last_login_at)}</p>
            )}
          </section>

          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Last activity</h3>
            <p>{formatDateTime(user.updated_at)}</p>
          </section>

          <section className="usr-drawer__section">
            <h3 className="usr-drawer__section-title">Recent audit events</h3>
            {workspace.auditLogs.length === 0 ? (
              <p className="usr-drawer__muted">No audit events recorded.</p>
            ) : (
              <ul className="usr-audit-list">
                {workspace.auditLogs.map((log) => (
                  <AuditRow key={log.id} log={log} />
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </aside>
  );
}
