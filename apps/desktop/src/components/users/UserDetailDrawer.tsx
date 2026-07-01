import { useState } from 'react';
import { X } from 'lucide-react';
import { formatDateTime, formatRelativeTime } from '../../lib/datetime';
import type { UsersWorkspaceState } from '../../hooks/useUsersWorkspace';
import {
  apiRoleLabel,
  formatPasswordAge,
  userDisplayName,
  userEffectiveStatus,
} from '../../lib/users';
import type { AuditLogEntry } from '../../services/api/AuditService';
import type { UserLoginEventSummary, UserSessionSummary } from '../../services/api/UserService';
import { PermissionViewer } from './PermissionViewer';
import { UserAvatar } from './UserAvatar';

interface UserDetailDrawerProps {
  workspace: Pick<
    UsersWorkspaceState,
    'selectedId' | 'selectedUser' | 'selectUser' | 'auditLogs' | 'rolePermissions' | 'drawerLoading'
  >;
}

type DrawerTab = 'profile' | 'permissions' | 'activity' | 'audit' | 'sessions';

const TABS: { id: DrawerTab; label: string }[] = [
  { id: 'profile', label: 'Profile' },
  { id: 'permissions', label: 'Permissions' },
  { id: 'activity', label: 'Recent activity' },
  { id: 'audit', label: 'Audit history' },
  { id: 'sessions', label: 'Sessions' },
];

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

function LoginEventRow({ event }: { event: UserLoginEventSummary }): JSX.Element {
  return (
    <li className="usr-audit-row">
      <span className="usr-audit-row__action">{event.success ? 'Login success' : 'Login failed'}</span>
      <span className="usr-audit-row__meta">
        {formatDateTime(event.created_at)}
        {event.ip_address ? ` · ${event.ip_address}` : ''}
      </span>
      {!event.success && event.failure_reason && (
        <span className="usr-audit-row__desc">{event.failure_reason.replaceAll('_', ' ')}</span>
      )}
    </li>
  );
}

function SessionRow({ session }: { session: UserSessionSummary }): JSX.Element {
  return (
    <li className="usr-session-row">
      <span className="usr-session-row__label">{session.device_label || 'Unknown device'}</span>
      <span className="usr-session-row__meta">
        {session.ip_address || 'No IP'}
        {session.last_used_at ? ` · Last used ${formatRelativeTime(session.last_used_at)}` : ''}
      </span>
      <span className="usr-session-row__meta">Expires {formatDateTime(session.expires_at)}</span>
    </li>
  );
}

export function UserDetailDrawer({ workspace }: UserDetailDrawerProps): JSX.Element | null {
  const user = workspace.selectedUser;
  const [tab, setTab] = useState<DrawerTab>('profile');
  if (!workspace.selectedId) return null;

  const status = user ? userEffectiveStatus(user) : null;

  return (
    <aside className="usr-drawer animate-slide-in" aria-label="User details">
      <header className="usr-drawer__header">
        <div className="usr-drawer__identity">
          {user && <UserAvatar user={user} size="md" />}
          <div>
            <p className="usr-drawer__eyebrow">Administration</p>
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

      {user && !workspace.drawerLoading && (
        <div className="usr-drawer__tabs" role="tablist" aria-label="User detail sections">
          {TABS.map((entry) => (
            <button
              key={entry.id}
              type="button"
              role="tab"
              aria-selected={tab === entry.id}
              className={`usr-drawer__tab ${tab === entry.id ? 'usr-drawer__tab--active' : ''}`}
              onClick={() => setTab(entry.id)}
            >
              {entry.label}
            </button>
          ))}
        </div>
      )}

      {workspace.drawerLoading && <p className="usr-drawer__loading">Loading user details…</p>}

      {user && !workspace.drawerLoading && (
        <div className="usr-drawer__body">
          {tab === 'profile' && (
            <section className="usr-drawer__section">
              <h3 className="usr-drawer__section-title">Profile</h3>
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
                  <dt>Role</dt>
                  <dd>{apiRoleLabel(user.role)}</dd>
                </div>
                <div>
                  <dt>Status</dt>
                  <dd>
                    {status && <span className={status.badgeClass}>{status.label}</span>}
                  </dd>
                </div>
                <div>
                  <dt>Last login</dt>
                  <dd>{user.last_login_at ? formatDateTime(user.last_login_at) : 'Never'}</dd>
                </div>
                <div>
                  <dt>Active sessions</dt>
                  <dd>{user.active_session_count}</dd>
                </div>
                <div>
                  <dt>Failed logins</dt>
                  <dd>{user.failed_login_count}</dd>
                </div>
                <div>
                  <dt>Password age</dt>
                  <dd>{formatPasswordAge(user.password_age_days)}</dd>
                </div>
                <div>
                  <dt>Created by</dt>
                  <dd>{user.created_by_display_name || '—'}</dd>
                </div>
                <div>
                  <dt>Created</dt>
                  <dd>{formatDateTime(user.created_at)}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{formatDateTime(user.updated_at)}</dd>
                </div>
              </dl>
            </section>
          )}

          {tab === 'permissions' && (
            <section className="usr-drawer__section usr-drawer__section--permissions">
              <h3 className="usr-drawer__section-title">Permissions</h3>
              <PermissionViewer rolePermissions={workspace.rolePermissions} selectedRole={user.role} compact />
            </section>
          )}

          {tab === 'activity' && (
            <section className="usr-drawer__section">
              <h3 className="usr-drawer__section-title">Recent activity</h3>
              {user.login_events.length === 0 ? (
                <p className="usr-drawer__muted">No login events recorded.</p>
              ) : (
                <ul className="usr-audit-list">
                  {user.login_events.map((event) => (
                    <LoginEventRow key={event.id} event={event} />
                  ))}
                </ul>
              )}
            </section>
          )}

          {tab === 'audit' && (
            <section className="usr-drawer__section">
              <h3 className="usr-drawer__section-title">Audit history</h3>
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
          )}

          {tab === 'sessions' && (
            <section className="usr-drawer__section">
              <h3 className="usr-drawer__section-title">Active sessions</h3>
              {user.sessions.length === 0 ? (
                <p className="usr-drawer__muted">No active sessions.</p>
              ) : (
                <ul className="usr-session-list">
                  {user.sessions.map((session) => (
                    <SessionRow key={session.id} session={session} />
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      )}
    </aside>
  );
}
