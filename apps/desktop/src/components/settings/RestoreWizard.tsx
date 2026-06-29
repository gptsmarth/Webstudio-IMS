import { useCallback, useMemo, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  FileUp,
  RotateCcw,
  Shield,
  X,
} from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import { formatBytes } from '../../lib/settings';
import {
  SettingsService,
  type BackupHistoryEntry,
  type BackupPreviewResult,
  type BackupRestoreResult,
  type BackupSource,
  type BackupValidateResult,
  type RestoreScope,
} from '../../services/api/SettingsService';
import { ModalPortal } from '../ModalPortal';

const WIZARD_STEPS = [
  { number: 1, label: 'Select' },
  { number: 2, label: 'Validate' },
  { number: 3, label: 'Preview' },
  { number: 4, label: 'Confirm' },
  { number: 5, label: 'Restore' },
  { number: 6, label: 'Verify' },
] as const;

const RESTORE_SCOPES: Array<{ id: RestoreScope; label: string; implemented: boolean }> = [
  { id: 'entire_database', label: 'Entire database', implemented: true },
  { id: 'settings_only', label: 'Settings only', implemented: true },
  { id: 'company_config', label: 'Company configuration', implemented: true },
  { id: 'users_only', label: 'Users only (future-ready)', implemented: false },
  { id: 'reports_only', label: 'Reports only (future-ready)', implemented: false },
];

function resolveSource(entry: BackupHistoryEntry): BackupSource {
  if (entry.filename.startsWith('webstudio-import-')) return 'imported';
  if (entry.trigger_type === 'scheduled') return 'scheduled';
  return 'local';
}

interface RestoreWizardProps {
  open: boolean;
  backups: BackupHistoryEntry[];
  initialFilename?: string | null;
  onClose: () => void;
  onComplete: () => Promise<void>;
}

export function RestoreWizard({
  open,
  backups,
  initialFilename,
  onClose,
  onComplete,
}: RestoreWizardProps): JSX.Element | null {
  const [step, setStep] = useState(1);
  const [selectedFilename, setSelectedFilename] = useState<string | null>(initialFilename ?? null);
  const [restoreScope, setRestoreScope] = useState<RestoreScope>('entire_database');
  const [createEmergencyBackup, setCreateEmergencyBackup] = useState(true);
  const [confirmText, setConfirmText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<BackupValidateResult | null>(null);
  const [preview, setPreview] = useState<BackupPreviewResult | null>(null);
  const [result, setResult] = useState<BackupRestoreResult | null>(null);

  const selectedBackup = useMemo(
    () => backups.find((item) => item.filename === selectedFilename) ?? null,
    [backups, selectedFilename],
  );

  const source = useMemo(
    () => (selectedBackup ? resolveSource(selectedBackup) : 'local'),
    [selectedBackup],
  );

  const reset = useCallback(() => {
    setStep(1);
    setSelectedFilename(initialFilename ?? null);
    setRestoreScope('entire_database');
    setCreateEmergencyBackup(true);
    setConfirmText('');
    setBusy(false);
    setError(null);
    setValidation(null);
    setPreview(null);
    setResult(null);
  }, [initialFilename]);

  const handleClose = () => {
    reset();
    onClose();
  };

  const runValidate = async () => {
    if (!selectedFilename) return;
    setBusy(true);
    setError(null);
    try {
      const response = await SettingsService.validateBackup(selectedFilename, source);
      setValidation(response);
      setStep(2);
    } catch {
      setError('Validation failed. Check the backup file and try again.');
    } finally {
      setBusy(false);
    }
  };

  const runPreview = async () => {
    if (!selectedFilename) return;
    setBusy(true);
    setError(null);
    try {
      const response = await SettingsService.previewRestore(selectedFilename, restoreScope, source);
      setPreview(response);
      setStep(3);
    } catch {
      setError('Unable to build restore preview.');
    } finally {
      setBusy(false);
    }
  };

  const runRestore = async () => {
    if (!selectedFilename) return;
    setBusy(true);
    setError(null);
    setStep(5);
    try {
      const response = await SettingsService.restoreBackup({
        filename: selectedFilename,
        restore_scope: restoreScope,
        source,
        create_emergency_backup: createEmergencyBackup,
        confirmed: true,
      });
      setResult(response);
      setStep(6);
      await onComplete();
    } catch {
      setError('Restore failed. Your emergency backup may still be available for rollback.');
      setStep(4);
    } finally {
      setBusy(false);
    }
  };

  const handleImport = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      const imported = await SettingsService.importBackup(file);
      setSelectedFilename(imported.filename);
      await onComplete();
    } catch {
      setError('Import failed. Ensure the file is a valid WEBSTUDIO backup archive.');
    } finally {
      setBusy(false);
    }
  };

  const handleRollback = async () => {
    if (!result?.emergency_backup_filename) return;
    if (!window.confirm('Roll back to the emergency backup created before this restore?')) return;
    setBusy(true);
    setError(null);
    try {
      const rollback = await SettingsService.rollbackBackup(result.emergency_backup_filename);
      setResult(rollback);
      await onComplete();
    } catch {
      setError('Rollback failed. Check server logs.');
    } finally {
      setBusy(false);
    }
  };

  if (!open) return null;

  const scopeOption = RESTORE_SCOPES.find((item) => item.id === restoreScope);
  const canProceedFromSelect = Boolean(selectedFilename);
  const canProceedFromValidate = (validation?.valid && validation.restore_allowed !== false) ?? false;
  const canProceedFromPreview = preview?.scope_implemented ?? false;
  const canConfirm = confirmText.trim().toUpperCase() === 'RESTORE';

  return (
    <ModalPortal>
      <div className="stg-restore-overlay" role="presentation" onClick={handleClose}>
      <div
        className="stg-restore-wizard animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-labelledby="restore-wizard-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="stg-restore-wizard__header">
          <div>
            <h2 id="restore-wizard-title">Restore Center</h2>
            <p className="stg-muted">Enterprise recovery workflow with validation and rollback.</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={handleClose} aria-label="Close">
            <X size={16} aria-hidden />
          </button>
        </header>

        <ol className="stg-restore-timeline" aria-label="Restore progress">
          {WIZARD_STEPS.map((wizardStep) => (
            <li
              key={wizardStep.number}
              className={[
                'stg-restore-timeline__item',
                step > wizardStep.number ? 'stg-restore-timeline__item--complete' : '',
                step === wizardStep.number ? 'stg-restore-timeline__item--current' : '',
              ].filter(Boolean).join(' ')}
            >
              <span className="stg-restore-timeline__dot">
                {step > wizardStep.number ? <Check size={12} aria-hidden /> : wizardStep.number}
              </span>
              <span>{wizardStep.label}</span>
            </li>
          ))}
        </ol>

        {error && (
          <div className="stg-restore-alert">
            <AlertTriangle size={14} aria-hidden />
            <span>{error}</span>
          </div>
        )}

        <div className="stg-restore-wizard__body">
          {step === 1 && (
            <section>
              <h3>Select backup</h3>
              <p className="stg-muted">Choose a manual, scheduled, or imported backup archive.</p>
              <div className="stg-restore-import">
                <label className="btn btn-ghost btn-sm">
                  <FileUp size={14} aria-hidden />
                  Import backup file
                  <input
                    type="file"
                    accept=".tar.gz,.sql,application/gzip,application/x-gzip"
                    hidden
                    disabled={busy}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) void handleImport(file);
                      event.currentTarget.value = '';
                    }}
                  />
                </label>
              </div>
              <ul className="stg-restore-select-list">
                {backups.map((item) => (
                  <li key={item.filename}>
                    <button
                      type="button"
                      className={[
                        'stg-restore-select-item',
                        selectedFilename === item.filename ? 'stg-restore-select-item--active' : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => setSelectedFilename(item.filename)}
                    >
                      <strong className="col-mono">{item.filename}</strong>
                      <span className="stg-muted">
                        {formatBytes(item.size_bytes)} · {formatDateTime(item.created_at)}
                      </span>
                      <span className="stg-muted">
                        {item.backup_type ?? 'full'} · {item.trigger_type ?? 'manual'}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {step === 2 && validation && (
            <section>
              <h3>Validation</h3>
              <div className="stg-restore-checks">
                <CheckRow label="Checksum" ok={validation.checksum_valid} warn={!validation.checksum_valid} />
                <CheckRow label="Integrity" ok={validation.integrity_valid} />
                <CheckRow label="Corruption" ok={!validation.corruption_detected} />
                <CheckRow label="Restore allowed" ok={validation.restore_allowed !== false} />
                <CheckRow label="Compatibility" ok={validation.compatibility === 'compatible'} warn={validation.compatibility === 'warning'} />
              </div>
              {validation.compatibility_report?.summary && (
                <p className="stg-muted">{validation.compatibility_report.summary}</p>
              )}
              <div className="stg-readonly-grid">
                <Readonly label="Company" value={validation.company_name ?? '—'} />
                <Readonly label="Created by" value={validation.created_by ?? '—'} />
                <Readonly label="Backup app version" value={validation.app_version ?? '—'} />
                <Readonly label="Backup version" value={validation.backup_version ?? '—'} />
                <Readonly label="Current app version" value={validation.current_app_version} />
                <Readonly label="Backup schema" value={validation.schema_version ?? '—'} />
                <Readonly label="Current schema" value={validation.current_schema_version} />
                <Readonly label="Migration required" value={validation.migration_required ? 'Yes' : 'No'} />
              </div>
              {validation.warnings.map((warning) => (
                <p key={warning} className="stg-backup-warning">{warning}</p>
              ))}
              {validation.errors.map((entry) => (
                <p key={entry} className="stg-backup-error">{entry}</p>
              ))}
            </section>
          )}

          {step === 3 && (
            <section>
              <h3>Preview</h3>
              <Field label="Restore scope">
                <div className="stg-restore-scope-list">
                  {RESTORE_SCOPES.map((scope) => (
                    <label key={scope.id} className="stg-restore-scope-option">
                      <input
                        type="radio"
                        name="restore-scope"
                        value={scope.id}
                        checked={restoreScope === scope.id}
                        disabled={!scope.implemented}
                        onChange={() => setRestoreScope(scope.id)}
                      />
                      <span>{scope.label}</span>
                    </label>
                  ))}
                </div>
              </Field>
              {preview && (
                <>
                  <div className="stg-readonly-grid">
                    <Readonly label="Backup name" value={preview.filename} />
                    <Readonly label="Company" value={preview.company_name ?? '—'} />
                    <Readonly label="Created" value={preview.timestamp ? formatDateTime(preview.timestamp) : '—'} />
                    <Readonly label="Created by" value={preview.created_by ?? '—'} />
                    <Readonly label="Version" value={preview.app_version ?? '—'} />
                    <Readonly label="Inventory records" value={String(preview.inventory_count ?? '—')} />
                    <Readonly label="Sales records" value={String(preview.sales_count ?? '—')} />
                    <Readonly label="Users" value={String(preview.users_count ?? '—')} />
                    <Readonly label="Database size" value={preview.database_size_bytes ? formatBytes(preview.database_size_bytes) : '—'} />
                    <Readonly label="Compressed size" value={formatBytes(preview.compressed_size_bytes ?? 0)} />
                    <Readonly label="Checksum status" value={preview.checksum_valid ? 'Valid' : 'Unverified'} />
                    <Readonly label="Schema compatibility" value={preview.schema_compatibility ?? '—'} />
                    <Readonly label="Affected areas" value={preview.affected_areas.join(', ') || '—'} />
                  </div>
                  {preview.compatibility_summary && (
                    <p className="stg-muted">{preview.compatibility_summary}</p>
                  )}
                  {preview.warnings.map((warning) => (
                    <p key={warning} className="stg-backup-warning">{warning}</p>
                  ))}
                </>
              )}
            </section>
          )}

          {step === 4 && (
            <section>
              <h3>Confirm restore</h3>
              <div className="stg-warning">
                <AlertTriangle size={14} aria-hidden />
                <span>
                  This will overwrite live data for <strong>{scopeOption?.label}</strong>.
                  {createEmergencyBackup && ' An emergency backup will be created automatically.'}
                </span>
              </div>
              <label className="stg-restore-confirm">
                <input
                  type="checkbox"
                  checked={createEmergencyBackup}
                  onChange={(event) => setCreateEmergencyBackup(event.target.checked)}
                />
                <span>Create emergency backup before restore (recommended)</span>
              </label>
              <Field label='Type RESTORE to confirm'>
                <input
                  className="input"
                  value={confirmText}
                  onChange={(event) => setConfirmText(event.target.value)}
                  placeholder="RESTORE"
                  autoComplete="off"
                />
              </Field>
            </section>
          )}

          {step === 5 && (
            <section className="stg-restore-progress">
              <h3>Restoring</h3>
              <div className="stg-restore-spinner" aria-hidden />
              <p className="stg-muted">Creating emergency backup, applying restore scope, and verifying…</p>
            </section>
          )}

          {step === 6 && result && (
            <section>
              <h3>Verification</h3>
              <div className={`stg-backup-verify stg-backup-verify--${result.verification_status}`}>
                {result.verification_status}
              </div>
              <div className="stg-readonly-grid">
                <Readonly label="Duration" value={`${result.duration_ms} ms`} />
                <Readonly label="Scope" value={result.restore_scope} />
                <Readonly
                  label="Emergency backup"
                  value={result.emergency_backup_filename ?? 'Not created'}
                />
              </div>
              {result.warnings.map((warning) => (
                <p key={warning} className="stg-backup-warning">{warning}</p>
              ))}
              {result.restart_required && (
                <div className="stg-warning">
                  <Shield size={14} aria-hidden />
                  <span>Backend restart is required for a full database restore to take full effect.</span>
                </div>
              )}
              {result.rollback_available && (result.rollback_recommended || result.emergency_backup_filename) && (
                <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void handleRollback()}>
                  <RotateCcw size={14} aria-hidden />
                  Roll back to previous state
                </button>
              )}
              {(result.verification_checks?.length ?? 0) > 0 && (
                <ul className="stg-restore-wizard__validation">
                  {result.verification_checks?.map((check) => (
                    <li key={check.key} className={`stg-recovery-check stg-recovery-check--${check.status}`}>
                      <strong>{check.name}</strong>
                      <span>{check.message}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>

        <footer className="stg-restore-wizard__footer">
          {step > 1 && step < 5 && (
            <button type="button" className="btn btn-ghost btn-sm" disabled={busy} onClick={() => setStep((value) => value - 1)}>
              <ChevronLeft size={14} aria-hidden />
              Back
            </button>
          )}
          <div className="stg-restore-wizard__footer-actions">
            {step === 1 && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!canProceedFromSelect || busy}
                onClick={() => void runValidate()}
              >
                Validate
                <ChevronRight size={14} aria-hidden />
              </button>
            )}
            {step === 2 && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!canProceedFromValidate || busy}
                onClick={() => void runPreview()}
              >
                Preview
                <ChevronRight size={14} aria-hidden />
              </button>
            )}
            {step === 3 && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!canProceedFromPreview || busy}
                onClick={() => setStep(4)}
              >
                Continue
                <ChevronRight size={14} aria-hidden />
              </button>
            )}
            {step === 4 && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!canConfirm || busy}
                onClick={() => void runRestore()}
              >
                Restore now
              </button>
            )}
            {step === 6 && (
              <button type="button" className="btn btn-primary btn-sm" onClick={handleClose}>
                Done
              </button>
            )}
          </div>
        </footer>
      </div>
    </div>
    </ModalPortal>
  );
}

function CheckRow({ label, ok, warn = false }: { label: string; ok: boolean; warn?: boolean }): JSX.Element {
  const status = ok ? 'ok' : warn ? 'warn' : 'fail';
  return (
    <div className={`stg-restore-check stg-restore-check--${status}`}>
      <span>{label}</span>
      <strong>{ok ? 'Pass' : warn ? 'Warning' : 'Fail'}</strong>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }): JSX.Element {
  return (
    <label className="stg-field">
      <span className="stg-field__label">{label}</span>
      {children}
    </label>
  );
}

function Readonly({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="stg-readonly">
      <span className="stg-readonly__label">{label}</span>
      <span className="stg-readonly__value">{value}</span>
    </div>
  );
}
