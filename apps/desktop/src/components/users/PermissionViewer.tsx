import { useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronRight, Search, X } from 'lucide-react';
import {
  buildPermissionModules,
  countGrantedPermissions,
  filterPermissionModules,
} from '../../lib/userPermissions';
import { apiRoleLabel } from '../../lib/users';
import type { RolePermissionsEntry } from '../../services/api/UserService';

interface PermissionViewerProps {
  rolePermissions: RolePermissionsEntry[];
  selectedRole?: string | null;
  compact?: boolean;
}

interface PermissionRoleSectionProps {
  entry: RolePermissionsEntry;
  compact: boolean;
  showRoleTitle: boolean;
}

function PermissionRoleSection({
  entry,
  compact,
  showRoleTitle,
}: PermissionRoleSectionProps): JSX.Element {
  const [search, setSearch] = useState('');
  const [showDenied, setShowDenied] = useState(false);
  const roleLabel = apiRoleLabel(entry.role);
  const modules = useMemo(
    () => filterPermissionModules(buildPermissionModules(entry.permissions, { roleLabel }), search),
    [entry.permissions, roleLabel, search],
  );
  const grantedCount = countGrantedPermissions(entry.permissions);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const toggleModule = (moduleId: string) => {
    setCollapsed((current) => ({ ...current, [moduleId]: !current[moduleId] }));
  };

  const visibleModules = modules
    .map((group) => {
      const capabilities =
        compact && !showDenied
          ? group.capabilities.filter((capability) => capability.granted)
          : group.capabilities;
      return { ...group, capabilities };
    })
    .filter((group) => group.capabilities.length > 0);

  return (
    <section className="usr-permissions__role">
      <div className="usr-permissions__summary">
        <div className="usr-permissions__summary-row">
          <span className="usr-permissions__summary-label">Role</span>
          <span className="usr-permissions__summary-value">{roleLabel}</span>
        </div>
        <div className="usr-permissions__summary-row">
          <span className="usr-permissions__summary-label">Permissions</span>
          <span className="usr-permissions__summary-value">{grantedCount} granted</span>
        </div>
      </div>

      {showRoleTitle && (
        <div className="usr-permissions__role-header">
          <h4 className="usr-permissions__role-title">{roleLabel}</h4>
        </div>
      )}

      <div className="usr-permissions__toolbar">
        <div className="usr-permissions__search">
          <Search size={14} className="usr-permissions__search-icon" aria-hidden />
          <input
            className="input usr-permissions__search-input"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search permissions…"
            aria-label="Search permissions"
          />
        </div>
        {compact && (
          <button
            type="button"
            className="btn btn-ghost btn-sm usr-permissions__toggle-denied"
            onClick={() => setShowDenied((current) => !current)}
          >
            {showDenied ? 'Hide denied' : 'Show denied'}
          </button>
        )}
      </div>

      <div className="usr-permissions__modules">
        {visibleModules.map((group) => {
          const isCollapsed = collapsed[group.moduleId] ?? compact;
          const grantedVisible = group.capabilities.filter(
            (capability) => capability.granted,
          ).length;
          return (
            <div key={group.moduleId} className="usr-permissions__module">
              <button
                type="button"
                className="usr-permissions__module-toggle"
                onClick={() => toggleModule(group.moduleId)}
                aria-expanded={!isCollapsed}
              >
                {isCollapsed ? (
                  <ChevronRight size={14} aria-hidden />
                ) : (
                  <ChevronDown size={14} aria-hidden />
                )}
                <span className="usr-permissions__module-name">{group.module}</span>
                <span className="usr-permissions__module-count">
                  {grantedVisible}/{group.capabilities.length}
                </span>
              </button>
              {!isCollapsed && (
                <ul className="usr-permissions__caps">
                  {group.capabilities.map((cap) => (
                    <li
                      key={cap.permission}
                      className={
                        cap.granted
                          ? 'usr-permissions__cap--granted'
                          : 'usr-permissions__cap--denied'
                      }
                    >
                      {cap.granted ? <Check size={12} aria-hidden /> : <X size={12} aria-hidden />}
                      <div className="usr-permissions__cap-body">
                        <span className="usr-permissions__cap-label">{cap.label}</span>
                        {!compact && (
                          <span className="usr-permissions__cap-meta">
                            Inherited from {cap.inheritedFrom}
                          </span>
                        )}
                        {!compact && (
                          <span className="usr-permissions__cap-desc">{cap.description}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
        {visibleModules.length === 0 && (
          <p className="usr-permissions__empty">
            {compact && !showDenied
              ? 'No granted permissions match your search.'
              : 'No permissions match your search.'}
          </p>
        )}
      </div>
    </section>
  );
}

export function PermissionViewer({
  rolePermissions,
  selectedRole,
  compact = false,
}: PermissionViewerProps): JSX.Element {
  const entries = selectedRole
    ? rolePermissions.filter((entry) => entry.role === selectedRole)
    : rolePermissions;

  if (entries.length === 0) {
    return <p className="usr-permissions__empty">Permission data unavailable.</p>;
  }

  return (
    <div className={`usr-permissions ${compact ? 'usr-permissions--compact' : ''}`}>
      {entries.map((entry) => (
        <PermissionRoleSection
          key={entry.role}
          entry={entry}
          compact={compact}
          showRoleTitle={!selectedRole && entries.length > 1}
        />
      ))}
    </div>
  );
}
