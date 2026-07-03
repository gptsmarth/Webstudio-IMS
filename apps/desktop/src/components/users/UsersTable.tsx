import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import type { UsersWorkspaceState } from '../../hooks/useUsersWorkspace';
import type { UserSortField } from '../../lib/users';
import {
  apiRoleLabel,
  formatPasswordAge,
  userDisplayName,
  userEffectiveStatus,
} from '../../lib/users';
import type { UserSummary } from '../../services/api/UserService';
import { UserAvatar } from './UserAvatar';

interface UsersTableProps {
  workspace: UsersWorkspaceState;
  currentUserId: number | null;
  onView: (user: UserSummary) => void;
  onMenu: (user: UserSummary, rect: DOMRect) => void;
}

export function UsersTable({
  workspace,
  currentUserId,
  onView,
  onMenu,
}: UsersTableProps): JSX.Element {
  const sortIcon = (field: UserSortField) => {
    if (workspace.sortField !== field) {
      return <ArrowUpDown size={12} className="usr-sort-icon usr-sort-icon--idle" />;
    }
    return workspace.sortDirection === 'asc' ? (
      <ArrowUp size={12} className="usr-sort-icon" />
    ) : (
      <ArrowDown size={12} className="usr-sort-icon" />
    );
  };

  const header = (label: string, field: UserSortField) => (
    <th>
      <button
        type="button"
        className="usr-table__th-sortable"
        onClick={() => workspace.toggleSort(field)}
      >
        {label} {sortIcon(field)}
      </button>
    </th>
  );

  return (
    <div className="usr-table-shell">
      <div className="usr-table-scroll">
        <table className="table usr-table">
          <thead className="usr-table__head">
            <tr>
              <th aria-label="Avatar" />
              {header('Name', 'display_name')}
              {header('Username', 'username')}
              {header('Role', 'role')}
              {header('Status', 'status')}
              {header('Last login', 'last_login_at')}
              <th>Sessions</th>
              <th>Failed logins</th>
              <th>Password age</th>
              <th>Created by</th>
              {header('Created', 'created_at')}
              <th aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {workspace.loading &&
              Array.from({ length: 6 }).map((_, index) => (
                <tr key={`sk-${index}`}>
                  <td colSpan={12}>
                    <div className="usr-table__skeleton animate-pulse" />
                  </td>
                </tr>
              ))}
            {!workspace.loading && workspace.items.length === 0 && (
              <tr>
                <td colSpan={12} className="usr-table__empty">
                  No users match the current filters.
                </td>
              </tr>
            )}
            {!workspace.loading &&
              workspace.items.map((user) => {
                const status = userEffectiveStatus(user);
                return (
                  <tr
                    key={user.id}
                    className={
                      [
                        'usr-table__row',
                        workspace.selectedId === user.id ? 'usr-table__row--selected' : '',
                      ]
                        .filter(Boolean)
                        .join(' ') || undefined
                    }
                    onClick={() => onView(user)}
                  >
                    <td>
                      <UserAvatar user={user} />
                    </td>
                    <td>
                      <span className="usr-table__name">{userDisplayName(user)}</span>
                      {currentUserId === user.id && <span className="usr-table__you">You</span>}
                    </td>
                    <td className="col-mono">{user.username}</td>
                    <td>{apiRoleLabel(user.role)}</td>
                    <td>
                      <span className={status.badgeClass}>{status.label}</span>
                    </td>
                    <td>{formatDateTime(user.last_login_at)}</td>
                    <td>{user.active_session_count}</td>
                    <td>{user.failed_login_count}</td>
                    <td>{formatPasswordAge(user.password_age_days)}</td>
                    <td className="usr-table__muted">{user.created_by_display_name || '—'}</td>
                    <td>{formatDateTime(user.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="usr-row-action"
                        aria-label={`Actions for ${user.username}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          onMenu(user, event.currentTarget.getBoundingClientRect());
                        }}
                      >
                        <MoreHorizontal size={14} />
                      </button>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
