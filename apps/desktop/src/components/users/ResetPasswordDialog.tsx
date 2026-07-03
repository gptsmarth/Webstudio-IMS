import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { userDisplayName } from '../../lib/users';
import { assessPasswordStrength, generateTemporaryPassword } from '../../lib/passwordStrength';
import type { UserSummary } from '../../services/api/UserService';

interface ResetPasswordDialogProps {
  open: boolean;
  user: UserSummary | null;
  loading: boolean;
  onClose: () => void;
  onConfirm: (temporaryPassword: string) => Promise<void>;
}

export function ResetPasswordDialog({
  open,
  user,
  loading,
  onClose,
  onConfirm,
}: ResetPasswordDialogProps): JSX.Element | null {
  const [password, setPassword] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const strength = assessPasswordStrength(password);

  useEffect(() => {
    if (!open) return;
    setPassword('');
    setConfirmed(false);
    setError(null);
  }, [open, user]);

  if (!open || !user) return null;

  const generatePassword = () => setPassword(generateTemporaryPassword());

  const submit = async () => {
    if (!strength.meetsMinimum) {
      setError('Password does not meet minimum strength.');
      return;
    }
    if (!confirmed) {
      setError('Confirm the password reset to continue.');
      return;
    }
    setError(null);
    try {
      await onConfirm(password);
      onClose();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to reset password.');
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div
        className="cat-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">Reset password</h2>
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
          <div className="usr-reset-banner">
            <AlertTriangle size={16} aria-hidden />
            <p>
              Set a temporary password for <strong>{userDisplayName(user)}</strong>. They will be
              required to change it on next login and all active sessions will be revoked.
            </p>
          </div>
          <label className="cat-field">
            <span>Temporary password</span>
            <div className="usr-password-field">
              <input
                className="input col-mono"
                type="text"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoFocus
              />
              <button type="button" className="btn btn-secondary btn-sm" onClick={generatePassword}>
                Generate
              </button>
            </div>
          </label>
          <div className="usr-strength">
            <div className="usr-strength__bar" aria-hidden>
              <span
                className={`usr-strength__fill usr-strength__fill--${strength.score}`}
                style={{ width: `${strength.percent}%` }}
              />
            </div>
            <span className="usr-strength__label">{strength.label}</span>
          </div>
          <label className="cat-field cat-field--checkbox usr-reset-confirm">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(event) => setConfirmed(event.target.checked)}
            />
            <span>I understand this will force a password change on next login</span>
          </label>
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
            {loading ? 'Resetting…' : 'Reset password'}
          </button>
        </footer>
      </div>
    </div>
  );
}
