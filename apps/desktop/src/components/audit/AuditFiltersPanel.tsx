import type { AuditFilters, AuditWorkspaceState } from '../../hooks/useAuditWorkspace';
import { AUDIT_ACTIONS, AUDIT_MODULES, AUDIT_SOURCES } from '../../lib/audit';
import type { UserRole } from '../../config/navigation';
import { formatRoleLabel } from '../../store/useAuthStore';
import type { Location } from '../../services/api/LocationService';
import type { UserSummary } from '../../services/api/UserService';

interface AuditFiltersPanelProps {
  filters: AuditFilters;
  setFilters: AuditWorkspaceState['setFilters'];
  resetFilters: AuditWorkspaceState['resetFilters'];
  users: UserSummary[];
  locations: Location[];
}

const ROLES: UserRole[] = ['main_admin', 'admin', 'salesperson'];

export function AuditFiltersPanel({
  filters,
  setFilters,
  resetFilters,
  users,
  locations,
}: AuditFiltersPanelProps): JSX.Element {
  const hasFilters = Boolean(
    filters.userId
    || filters.role
    || filters.operation
    || filters.module
    || filters.source
    || filters.locationId
    || filters.result
    || filters.serialNumber
    || filters.invoiceNumber
    || filters.modelNumber
    || filters.dateFrom
    || filters.dateTo,
  );

  return (
    <div className="aud-filters">
      <label className="aud-filters__field">
        <span>User</span>
        <select
          className="input"
          value={filters.userId ?? ''}
          onChange={(event) =>
            setFilters({ userId: event.target.value ? Number(event.target.value) : null })
          }
        >
          <option value="">All users</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.display_name ?? user.username}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Role</span>
        <select className="input" value={filters.role} onChange={(event) => setFilters({ role: event.target.value })}>
          <option value="">All roles</option>
          {ROLES.map((role) => (
            <option key={role} value={role}>
              {formatRoleLabel(role)}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Operation</span>
        <select
          className="input"
          value={filters.operation}
          onChange={(event) => setFilters({ operation: event.target.value as AuditFilters['operation'] })}
        >
          <option value="">All operations</option>
          {AUDIT_ACTIONS.map((action) => (
            <option key={action} value={action}>
              {action.replaceAll('_', ' ')}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Module</span>
        <select className="input" value={filters.module} onChange={(event) => setFilters({ module: event.target.value })}>
          <option value="">All modules</option>
          {AUDIT_MODULES.map((module) => (
            <option key={module} value={module}>
              {module}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Source</span>
        <select
          className="input"
          value={filters.source}
          onChange={(event) => setFilters({ source: event.target.value as AuditFilters['source'] })}
        >
          <option value="">All sources</option>
          {AUDIT_SOURCES.map((source) => (
            <option key={source} value={source}>
              {source.replaceAll('_', ' ')}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Location</span>
        <select
          className="input"
          value={filters.locationId ?? ''}
          onChange={(event) =>
            setFilters({ locationId: event.target.value ? Number(event.target.value) : null })
          }
        >
          <option value="">All locations</option>
          {locations.map((location) => (
            <option key={location.id} value={location.id}>
              {location.name}
            </option>
          ))}
        </select>
      </label>
      <label className="aud-filters__field">
        <span>Result</span>
        <select
          className="input"
          value={filters.result}
          onChange={(event) => setFilters({ result: event.target.value as AuditFilters['result'] })}
        >
          <option value="">All results</option>
          <option value="success">Success</option>
          <option value="failure">Failure</option>
        </select>
      </label>
      <label className="aud-filters__field">
        <span>From</span>
        <input className="input" type="date" value={filters.dateFrom} onChange={(event) => setFilters({ dateFrom: event.target.value })} />
      </label>
      <label className="aud-filters__field">
        <span>To</span>
        <input className="input" type="date" value={filters.dateTo} onChange={(event) => setFilters({ dateTo: event.target.value })} />
      </label>
      {hasFilters && (
        <button type="button" className="btn btn-ghost btn-sm aud-filters__reset" onClick={resetFilters}>
          Clear filters
        </button>
      )}
    </div>
  );
}
