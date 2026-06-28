import { AlertTriangle, X } from 'lucide-react';
import { userDisplayName } from '../../lib/users';
import type { UserSummary } from '../../services/api/UserService';

interface ConfirmUserActionDialogProps {
  open: boolean;
  user: UserSummary | null;
  title: string;
  message: string;
  confirmLabel: string;
  loading: boolean;
  danger?: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export function ConfirmUserActionDialog({
  open,
  user,
  title,
  message,
  confirmLabel,
  loading,
  danger = false,
  onClose,
  onConfirm,
}: ConfirmUserActionDialogProps): JSX.Element | null {
  if (!open || !user) return null;

  const submit = async () => {
    try {
      await onConfirm();
      onClose();
    } catch {
      // Parent surfaces action errors
    }
  };

  return (
    <div className="cat-dialog-overlay" role="presentation" onClick={onClose}>
      <div className="cat-dialog animate-slide-in" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <header className="cat-dialog__header">
          <h2 className="cat-dialog__title">{title}</h2>
          <button type="button" className="app-toolbar-icon-btn" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </header>
        <div className="cat-dialog__body">
          <div className={`usr-reset-banner ${danger ? 'usr-reset-banner--danger' : ''}`}>
            <AlertTriangle size={16} aria-hidden />
            <p>
              {message} <strong>{userDisplayName(user)}</strong> ({user.username})?
            </p>
          </div>
        </div>
        <footer className="cat-dialog__footer">
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            type="button"
            className={danger ? 'btn btn-danger btn-sm' : 'btn btn-primary btn-sm'}
            onClick={() => void submit()}
            disabled={loading}
          >
            {loading ? 'Working…' : confirmLabel}
          </button>
        </footer>
      </div>
    </div>
  );
}
