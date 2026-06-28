import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { HUMAN_USER_ROLES, apiRoleLabel } from '../../lib/users';
import { assessPasswordStrength, generateTemporaryPassword } from '../../lib/passwordStrength';
import type { UserDetail, UserRole } from '../../services/api/UserService';

interface UserFormDialogProps {
  open: boolean;
  user: UserDetail | null;
  loading: boolean;
  onClose: () => void;
  onCreate: (payload: {
    username: string;
    display_name?: string | null;
    role: UserRole;
    temporary_password: string;
  }) => Promise<void>;
  onUpdate: (displayName: string) => Promise<void>;
}

export function UserFormDialog({
  open,
  user,
  loading,
  onClose,
  onCreate,
  onUpdate,
}: UserFormDialogProps): JSX.Element | null {
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState<UserRole>('salesperson');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const isEdit = Boolean(user);
  const strength = assessPasswordStrength(password);

  useEffect(() => {
    if (!open) return;
    setUsername(user?.username ?? '');
    setDisplayName(user?.display_name ?? '');
    setRole(user?.role ?? 'salesperson');
    setPassword('');
    setError(null);
  }, [open, user]);

  if (!open) return null;

  const generatePassword = () => {
    const generated = generateTemporaryPassword();
    setPassword(generated);
  };

  const submit = async () => {
    if (isEdit) {
      if (!displayName.trim()) {
        setError('Full name is required.');
        return;
      }
      setError(null);
      try {
        await onUpdate(displayName.trim());
        onClose();
      } catch (err: unknown) {
        const message = err as { message?: string };
        setError(message.message ?? 'Unable to save user.');
      }
      return;
    }

    if (!username.trim()) {
      setError('Username is required.');
      return;
    }
    if (!displayName.trim()) {
      setError('Full name is required.');
      return;
    }
    if (!strength.meetsMinimum) {
      setError('Temporary password does not meet minimum strength.');
      return;
    }
    setError(null);
    try {
      await onCreate({
        username: username.trim(),
        display_name: displayName.trim(),
        role,
        temporary_password: password,
      });
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to create user.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">{isEdit ? 'Edit user' : 'Create user'}</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body cat-dialog__grid">
          {!isEdit && (
            <label className="cat-field">
              <span>Username</span>
              <input className="input col-mono" value={username} onChange={(event) => setUsername(event.target.value)} autoFocus />
            </label>
          )}
          <label className="cat-field">
            <span>Full name</span>
            <input className="input" value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoFocus={isEdit} />
          </label>
          {!isEdit && (
            <label className="cat-field">
              <span>Role</span>
              <select className="input" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
                {HUMAN_USER_ROLES.map((entry) => (
                  <option key={entry} value={entry}>
                    {apiRoleLabel(entry)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {!isEdit && (
            <>
              <label className="cat-field cat-field--full">
                <span>Temporary password</span>
                <div className="usr-password-field">
                  <input
                    className="input col-mono"
                    type="text"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                  <button type="button" className="btn btn-secondary btn-sm" onClick={generatePassword}>
                    Generate
                  </button>
                </div>
              </label>
              <div className="cat-field cat-field--full">
                <div className="usr-strength">
                  <div className="usr-strength__bar" aria-hidden>
                    <span className={`usr-strength__fill usr-strength__fill--${strength.score}`} style={{ width: `${strength.percent}%` }} />
                  </div>
                  <span className="usr-strength__label">{strength.label}</span>
                </div>
                <p className="usr-strength__hint">User must change password on first login.</p>
              </div>
            </>
          )}
          {error && <p className="cat-dialog__error cat-field--full">{error}</p>}
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={() => void submit()} disabled={loading}>
            {loading ? 'Saving…' : isEdit ? 'Save changes' : 'Create user'}
          </button>
        </footer>
      </div>
    </div>
  );
}
