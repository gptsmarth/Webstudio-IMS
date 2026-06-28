import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { HUMAN_USER_ROLES, apiRoleLabel, userDisplayName } from '../../lib/users';
import { PermissionViewer } from './PermissionViewer';
import type { RolePermissionsEntry, UserRole, UserSummary } from '../../services/api/UserService';

interface ChangeRoleDialogProps {
  open: boolean;
  user: UserSummary | null;
  rolePermissions: RolePermissionsEntry[];
  loading: boolean;
  onClose: () => void;
  onConfirm: (role: UserRole) => Promise<void>;
}

export function ChangeRoleDialog({
  open,
  user,
  rolePermissions,
  loading,
  onClose,
  onConfirm,
}: ChangeRoleDialogProps): JSX.Element | null {
  const [role, setRole] = useState<UserRole>('salesperson');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !user) return;
    setRole(user.role === 'service_account' ? 'salesperson' : user.role);
    setError(null);
  }, [open, user]);

  if (!open || !user) return null;

  const submit = async () => {
    if (role === user.role) {
      setError('Select a different role.');
      return;
    }
    setError(null);
    try {
      await onConfirm(role);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to change role.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog cat-dialog--wide animate-slide-in" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Change role</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body">
          <p className="usr-dialog-intro">
            Update role for <strong>{userDisplayName(user)}</strong> ({user.username}).
          </p>
          <label className="cat-field">
            <span>New role</span>
            <select className="input" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
              {HUMAN_USER_ROLES.map((entry) => (
                <option key={entry} value={entry}>
                  {apiRoleLabel(entry)}
                </option>
              ))}
            </select>
          </label>
          <div className="usr-dialog-permissions">
            <p className="usr-dialog-permissions__title">Effective permissions</p>
            <PermissionViewer rolePermissions={rolePermissions} selectedRole={role} compact />
          </div>
          {error && <p className="cat-dialog__error">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Saving…' : 'Change role'}
          </button>
        </footer>
      </div>
    </div>
  );
}
