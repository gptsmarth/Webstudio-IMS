import { useCallback, useEffect, useState } from 'react';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  HeartPulse,
  RefreshCw,
  Shield,
  Wand2,
  X,
} from 'lucide-react';
import {
  SettingsService,
  type RecoveryCenterDashboard,
  type RecoveryValidationResult,
} from '../../services/api/SettingsService';
import { ModalPortal } from '../ModalPortal';

const WIZARD_STEPS = [
  { number: 1, label: 'Assessment' },
  { number: 2, label: 'Validation' },
  { number: 3, label: 'Recovery' },
  { number: 4, label: 'Restart' },
  { number: 5, label: 'Verification' },
] as const;

interface RecoveryWizardProps {
  open: boolean;
  onClose: () => void;
  onOpenRestore: () => void;
  onRunBackup: () => Promise<void>;
  onComplete: () => Promise<void>;
}

export function RecoveryWizard({
  open,
  onClose,
  onOpenRestore,
  onRunBackup,
  onComplete,
}: RecoveryWizardProps): JSX.Element | null {
  const [step, setStep] = useState(1);
  const [center, setCenter] = useState<RecoveryCenterDashboard | null>(null);
  const [validation, setValidation] = useState<RecoveryValidationResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restartAcknowledged, setRestartAcknowledged] = useState(false);

  const loadCenter = useCallback(async () => {
    const dashboard = await SettingsService.getRecoveryCenter();
    setCenter(dashboard);
  }, []);

  useEffect(() => {
    if (!open) return;
    setStep(1);
    setValidation(null);
    setError(null);
    setRestartAcknowledged(false);
    void loadCenter();
  }, [open, loadCenter]);

  if (!open) return null;

  const runValidation = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await SettingsService.runRecoveryValidation();
      setValidation(result);
      setStep(2);
    } catch {
      setError('Recovery validation failed.');
    } finally {
      setBusy(false);
    }
  };

  const finish = async () => {
    await onComplete();
    onClose();
  };

  return (
    <ModalPortal>
      <div className="stg-restore-overlay" role="presentation" onClick={onClose}>
        <div
          className="stg-recovery-wizard animate-slide-in"
          role="dialog"
          aria-modal="true"
          aria-label="Recovery wizard"
          onClick={(event) => event.stopPropagation()}
        >
          <header className="stg-recovery-wizard__header">
            <div>
              <h2>
                <Wand2 size={18} aria-hidden /> Recovery wizard
              </h2>
              <p className="stg-muted">
                Guide administrators through validation, recovery, and verification.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-icon"
              onClick={onClose}
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </header>

          <ol className="stg-recovery-wizard__steps">
            {WIZARD_STEPS.map((item) => (
              <li
                key={item.number}
                className={step === item.number ? 'is-active' : step > item.number ? 'is-done' : ''}
              >
                <span>{item.number}</span>
                {item.label}
              </li>
            ))}
          </ol>

          {error && <p className="stg-backup-warning">{error}</p>}

          <div className="stg-recovery-wizard__body">
            {step === 1 && center && (
              <>
                <div
                  className={`stg-recovery-banner stg-recovery-status--${center.system_health === 'healthy' ? 'healthy' : 'warning'}`}
                >
                  <HeartPulse size={16} aria-hidden />
                  <div>
                    <strong>System health: {center.system_health}</strong>
                    <p className="stg-muted">Recovery readiness: {center.recovery_readiness}</p>
                  </div>
                </div>
                <ul className="stg-recovery-wizard__checks">
                  <li>Database: {center.database_status}</li>
                  <li>Backup: {center.backup_status}</li>
                  <li>Storage: {center.storage_status}</li>
                  <li>{center.health_issues.length} health issue(s) detected</li>
                </ul>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  disabled={busy}
                  onClick={() => void runValidation()}
                >
                  <Shield size={14} aria-hidden />
                  Run validation
                </button>
              </>
            )}

            {step === 2 && validation && (
              <>
                <p className={`stg-backup-verify stg-backup-verify--${validation.overall_status}`}>
                  Overall: {validation.overall_status}
                </p>
                <ul className="stg-recovery-wizard__validation">
                  {validation.checks.map((check) => (
                    <li
                      key={check.key}
                      className={`stg-recovery-check stg-recovery-check--${check.status}`}
                    >
                      <strong>{check.name}</strong>
                      <span>{check.message}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}

            {step === 3 && (
              <>
                <p className="stg-muted">Choose a recovery action based on validation results.</p>
                <div className="stg-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      onClose();
                      onOpenRestore();
                    }}
                  >
                    <RefreshCw size={14} aria-hidden />
                    Restore from backup
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void onRunBackup()}
                  >
                    Run fresh backup
                  </button>
                </div>
              </>
            )}

            {step === 4 && (
              <>
                <p>
                  If you restored the entire database, restart the WEBSTUDIO backend and desktop
                  client so connections reload with the recovered data.
                </p>
                <label className="stg-check">
                  <input
                    type="checkbox"
                    checked={restartAcknowledged}
                    onChange={(e) => setRestartAcknowledged(e.target.checked)}
                  />
                  I understand restart may be required after a full database restore.
                </label>
              </>
            )}

            {step === 5 && (
              <>
                <p className="stg-muted">Re-check system health after recovery actions.</p>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void loadCenter()}
                >
                  Refresh status
                </button>
                {center && (
                  <p
                    className={`stg-backup-verify stg-backup-verify--${center.recovery_readiness === 'ready' ? 'success' : 'warning'}`}
                  >
                    Recovery readiness: {center.recovery_readiness}
                  </p>
                )}
              </>
            )}
          </div>

          <footer className="stg-recovery-wizard__footer">
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={step <= 1 || busy}
              onClick={() => setStep((value) => Math.max(1, value - 1))}
            >
              <ChevronLeft size={14} aria-hidden />
              Back
            </button>
            {step < 5 ? (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={busy || (step === 4 && !restartAcknowledged)}
                onClick={() => setStep((value) => Math.min(5, value + 1))}
              >
                Next
                <ChevronRight size={14} aria-hidden />
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => void finish()}
              >
                <Check size={14} aria-hidden />
                Complete
              </button>
            )}
          </footer>
        </div>
      </div>
    </ModalPortal>
  );
}
