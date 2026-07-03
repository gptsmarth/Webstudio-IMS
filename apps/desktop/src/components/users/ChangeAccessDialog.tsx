import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { HUMAN_USER_ROLES, apiRoleLabel, userDisplayName } from '../../lib/users';
import { PermissionViewer } from './PermissionViewer';
import {
  AccessRoleService,
  type CustomAccessRoleSummary,
} from '../../services/api/AccessRoleService';
import type { RolePermissionsEntry, UserRole, UserSummary } from '../../services/api/UserService';

interface ChangeAccessDialogProps {
  open: boolean;
  user: UserSummary | null;
  rolePermissions: RolePermissionsEntry[];
  loading: boolean;
  onClose: () => void;
  onConfirmBuiltin: (role: UserRole) => Promise<void>;
  onConfirmCustom: (customRoleId: number) => Promise<void>;
}

export function ChangeAccessDialog({
  open,
  user,
  rolePermissions,
  loading,
  onClose,
  onConfirmBuiltin,
  onConfirmCustom,
}: ChangeAccessDialogProps): JSX.Element | null {
  const [accessType, setAccessType] = useState<'builtin' | 'custom'>('builtin');
  const [role, setRole] = useState<UserRole>('salesperson');
  const [customRoleId, setCustomRoleId] = useState<number | ''>('');
  const [customRoles, setCustomRoles] = useState<CustomAccessRoleSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    void AccessRoleService.listRoles()
      .then(setCustomRoles)
      .catch(() => setCustomRoles([]));
  }, [open]);

  useEffect(() => {
    if (!open || !user) return;
    if (user.custom_access_role_id) {
      setAccessType('custom');
      setCustomRoleId(user.custom_access_role_id);
    } else {
      setAccessType('builtin');
      setRole(user.role === 'service_account' ? 'salesperson' : user.role);
      setCustomRoleId('');
    }
    setError(null);
  }, [open, user]);

  if (!open || !user) return null;

  const submit = async () => {
    setError(null);
    try {
      if (accessType === 'builtin') {
        if (role === user.role && !user.custom_access_role_id) {
          setError('Select a different built-in role or choose a custom role.');
          return;
        }
        await onConfirmBuiltin(role);
      } else {
        if (customRoleId === '') {
          setError('Select a custom access role.');
          return;
        }
        await onConfirmCustom(Number(customRoleId));
      }
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to update access.');
    }
  };

  const previewRole = accessType === 'builtin' ? role : 'salesperson';

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="cat-dialog cat-dialog--wide animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Change access</h2>
          <button
            type="button"
            className="app-toolbar-icon-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body">
          <p className="usr-dialog-intro">
            Update access for <strong>{userDisplayName(user)}</strong> ({user.username}).
          </p>
          <label className="cat-field">
            <span>Access type</span>
            <select
              className="input"
              value={accessType}
              onChange={(event) => setAccessType(event.target.value as 'builtin' | 'custom')}
            >
              <option value="builtin">Built-in role template</option>
              <option value="custom">Custom access role</option>
            </select>
          </label>
          {accessType === 'builtin' ? (
            <label className="cat-field">
              <span>Built-in role</span>
              <select
                className="input"
                value={role}
                onChange={(event) => setRole(event.target.value as UserRole)}
              >
                {HUMAN_USER_ROLES.map((entry) => (
                  <option key={entry} value={entry}>
                    {apiRoleLabel(entry)}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <label className="cat-field">
              <span>Custom role</span>
              <select
                className="input"
                value={customRoleId}
                onChange={(event) =>
                  setCustomRoleId(event.target.value ? Number(event.target.value) : '')
                }
              >
                <option value="">Select a role…</option>
                {customRoles.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.name} ({entry.permission_count} permissions)
                  </option>
                ))}
              </select>
            </label>
          )}
          {accessType === 'builtin' && (
            <div className="usr-dialog-permissions">
              <p className="usr-dialog-permissions__title">Effective permissions</p>
              <PermissionViewer
                rolePermissions={rolePermissions}
                selectedRole={previewRole}
                compact
              />
            </div>
          )}
          {error && <p className="cat-dialog__error">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={onClose}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => void submit()}
            disabled={loading}
          >
            {loading ? 'Saving…' : 'Save access'}
          </button>
        </footer>
      </div>
    </div>
  );
}
