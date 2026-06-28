import { Check, X } from 'lucide-react';
import { buildPermissionModules, listUnknownPermissions } from '../../lib/userPermissions';
import { apiRoleLabel } from '../../lib/users';
import type { RolePermissionsEntry } from '../../services/api/UserService';

interface PermissionViewerProps {
  rolePermissions: RolePermissionsEntry[];
  selectedRole?: string | null;
  compact?: boolean;
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
      {entries.map((entry) => {
        const modules = buildPermissionModules(entry.permissions);
        const unknown = listUnknownPermissions(entry.permissions);
        return (
          <section key={entry.role} className="usr-permissions__role">
            {!selectedRole && <h4 className="usr-permissions__role-title">{apiRoleLabel(entry.role)}</h4>}
            <div className="usr-permissions__modules">
              {modules.map((group) => (
                <div key={group.module} className="usr-permissions__module">
                  <p className="usr-permissions__module-name">{group.module}</p>
                  <ul className="usr-permissions__caps">
                    {group.capabilities.map((cap) => (
                      <li key={cap.label} className={cap.granted ? 'usr-permissions__cap--granted' : 'usr-permissions__cap--denied'}>
                        {cap.granted ? <Check size={12} aria-hidden /> : <X size={12} aria-hidden />}
                        <span>{cap.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
              {unknown.length > 0 && (
                <div className="usr-permissions__module">
                  <p className="usr-permissions__module-name">Other</p>
                  <ul className="usr-permissions__caps">
                    {unknown.map((permission) => (
                      <li key={permission} className="usr-permissions__cap--granted">
                        <Check size={12} aria-hidden />
                        <span>{permission}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}
