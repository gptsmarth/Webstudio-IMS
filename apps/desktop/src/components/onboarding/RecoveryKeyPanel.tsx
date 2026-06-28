import { useState } from 'react';
import { AlertCircle, CheckCircle2, Copy, Printer } from 'lucide-react';

interface RecoveryKeyPanelProps {
  recoveryKey: string;
  isDemo?: boolean;
  title?: string;
  description?: string;
  confirmLabel?: string;
  hasConfirmed: boolean;
  onConfirmChange: (confirmed: boolean) => void;
}

export function RecoveryKeyPanel({
  recoveryKey,
  isDemo = false,
  title = 'Master Recovery Key',
  description = 'This key is the only way to reset the administrator password if it is ever lost. Store it somewhere safe — a password manager, a printed sheet in a secure location, or an encrypted note.',
  confirmLabel = 'I confirm that I have copied and safely stored the recovery key. I understand this key cannot be recovered if lost.',
  hasConfirmed,
  onConfirmChange,
}: RecoveryKeyPanelProps): JSX.Element {
  const [hasCopied, setHasCopied] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const handleCopyKey = () => {
    void navigator.clipboard.writeText(recoveryKey);
    setHasCopied(true);
    setCopyFeedback('Copied — store this in a safe place.');
    setTimeout(() => setCopyFeedback(null), 6000);
  };

  return (
    <div className="recovery-key-panel">
      <div>
        <h2 className="recovery-key-panel__title">{title}</h2>
        <p className="recovery-key-panel__description">{description}</p>
      </div>

      <div className="alert alert-warning">
        <AlertCircle size={14} aria-hidden="true" />
        <span>
          <strong>This key will never be shown again.</strong> If you lose it, the administrator account cannot be recovered.
        </span>
      </div>

      <div>
        <p className="recovery-key-panel__label">Recovery Key</p>
        <div className="recovery-key-panel__key-box">
          <code className={`recovery-key-panel__key ${isDemo ? 'recovery-key-panel__key--demo' : ''}`}>
            {isDemo ? '[UI PREVIEW MODE — NO REAL KEY]' : recoveryKey}
          </code>

          {!isDemo && (
            <div className="recovery-key-panel__actions">
              <button type="button" className="btn btn-secondary btn-sm" onClick={handleCopyKey} title="Copy to clipboard">
                {hasCopied ? <CheckCircle2 size={13} style={{ color: 'var(--color-success)' }} /> : <Copy size={13} />}
                <span>{hasCopied ? 'Copied' : 'Copy'}</span>
              </button>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => window.print()} title="Print key sheet">
                <Printer size={13} />
              </button>
            </div>
          )}
        </div>

        {copyFeedback && <p className="recovery-key-panel__copy-feedback">{copyFeedback}</p>}
      </div>

      <label className={`recovery-key-panel__confirm ${hasConfirmed ? 'recovery-key-panel__confirm--checked' : ''}`}>
        <input
          type="checkbox"
          checked={hasConfirmed}
          onChange={(e) => onConfirmChange(e.target.checked)}
          className="recovery-key-panel__checkbox"
        />
        <span>{confirmLabel}</span>
      </label>
    </div>
  );
}
