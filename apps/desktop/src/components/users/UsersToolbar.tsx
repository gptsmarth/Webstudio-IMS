import { Search, UserPlus } from 'lucide-react';
import { P, permissionDeniedTooltip } from '../../services/PermissionService';
import type { UsersWorkspaceState } from '../../hooks/useUsersWorkspace';

interface UsersToolbarProps {
  workspace: Pick<UsersWorkspaceState, 'search' | 'setSearch' | 'loading'>;
  onCreate: () => void;
  canCreate?: boolean;
}

export function UsersToolbar({
  workspace,
  onCreate,
  canCreate = true,
}: UsersToolbarProps): JSX.Element {
  return (
    <div className="usr-toolbar">
      <div className="usr-toolbar__search">
        <Search size={14} className="usr-toolbar__search-icon" aria-hidden />
        <input
          className="input usr-toolbar__search-input"
          type="search"
          placeholder="Search by name or username…"
          value={workspace.search}
          onChange={(event) => workspace.setSearch(event.target.value)}
          aria-label="Search users"
        />
      </div>
      <div className="usr-toolbar__actions">
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={onCreate}
          disabled={workspace.loading || !canCreate}
          title={canCreate ? undefined : permissionDeniedTooltip(P.users.create)}
        >
          <UserPlus size={14} aria-hidden />
          Create user
        </button>
      </div>
    </div>
  );
}
