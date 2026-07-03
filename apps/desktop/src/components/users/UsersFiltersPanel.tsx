import type { UsersFilters, UsersWorkspaceState } from '../../hooks/useUsersWorkspace';
import { HUMAN_USER_ROLES, apiRoleLabel } from '../../lib/users';

interface UsersFiltersPanelProps {
  filters: UsersFilters;
  setFilters: UsersWorkspaceState['setFilters'];
  resetFilters: UsersWorkspaceState['resetFilters'];
}

export function UsersFiltersPanel({
  filters,
  setFilters,
  resetFilters,
}: UsersFiltersPanelProps): JSX.Element {
  const hasFilters = Boolean(
    filters.role || filters.status || filters.createdFrom || filters.createdTo,
  );

  return (
    <div className="usr-filters">
      <label className="usr-filters__field">
        <span>Role</span>
        <select
          className="input"
          value={filters.role}
          onChange={(event) => setFilters({ role: event.target.value as UsersFilters['role'] })}
        >
          <option value="">All roles</option>
          {HUMAN_USER_ROLES.map((role) => (
            <option key={role} value={role}>
              {apiRoleLabel(role)}
            </option>
          ))}
        </select>
      </label>
      <label className="usr-filters__field">
        <span>Status</span>
        <select
          className="input"
          value={filters.status}
          onChange={(event) => setFilters({ status: event.target.value as UsersFilters['status'] })}
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="disabled">Disabled</option>
        </select>
      </label>
      <label className="usr-filters__field">
        <span>Created from</span>
        <input
          className="input"
          type="date"
          value={filters.createdFrom}
          onChange={(event) => setFilters({ createdFrom: event.target.value })}
        />
      </label>
      <label className="usr-filters__field">
        <span>Created to</span>
        <input
          className="input"
          type="date"
          value={filters.createdTo}
          onChange={(event) => setFilters({ createdTo: event.target.value })}
        />
      </label>
      {hasFilters && (
        <button
          type="button"
          className="btn btn-ghost btn-sm usr-filters__reset"
          onClick={resetFilters}
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
