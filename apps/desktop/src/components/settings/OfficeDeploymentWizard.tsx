import { useCallback, useEffect, useState } from 'react';
import {
  Check,
  ChevronLeft,
  ChevronRight,
  Download,
  Network,
  RefreshCw,
  Server,
  X,
} from 'lucide-react';
import {
  DeploymentService,
  type OfficeDeploymentCompleteResult,
  type OfficeDeploymentDetection,
  type OfficeDeploymentSummary,
} from '../../services/api/DeploymentService';
import { ModalPortal } from '../ModalPortal';

const WIZARD_STEPS = [
  { number: 1, label: 'Welcome' },
  { number: 2, label: 'Detect' },
  { number: 3, label: 'Configure' },
  { number: 4, label: 'Summary' },
] as const;

interface OfficeDeploymentWizardProps {
  open: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

function statusClass(status: string): string {
  if (status === 'passed') return 'stg-recovery-status--healthy';
  if (status === 'failed') return 'stg-recovery-status--critical';
  return 'stg-recovery-status--warning';
}

export function OfficeDeploymentWizard({
  open,
  onClose,
  onComplete,
}: OfficeDeploymentWizardProps): JSX.Element | null {
  const [step, setStep] = useState(1);
  const [detection, setDetection] = useState<OfficeDeploymentDetection | null>(null);
  const [completeResult, setCompleteResult] = useState<OfficeDeploymentCompleteResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setStep(1);
    setDetection(null);
    setCompleteResult(null);
    setError(null);
  }, [open]);

  const runDetection = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await DeploymentService.detect();
      setDetection(result);
      setStep(2);
    } catch {
      setError('Environment detection failed.');
    } finally {
      setBusy(false);
    }
  }, []);

  const finishDeployment = async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await DeploymentService.complete();
      setCompleteResult(result);
      setDetection(result.detection);
      setStep(4);
      await onComplete?.();
    } catch {
      setError('Could not save deployment configuration.');
    } finally {
      setBusy(false);
    }
  };

  const downloadSummary = () => {
    const summary: OfficeDeploymentSummary | undefined = completeResult?.summary;
    if (!summary) return;
    const blob = new Blob([JSON.stringify(summary, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `webstudio-deployment-summary-${summary.generated_at.slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (!open) return null;

  return (
    <ModalPortal>
      <div className="stg-restore-overlay" role="presentation" onClick={onClose}>
        <div
          className="stg-recovery-wizard animate-slide-in"
          role="dialog"
          aria-modal="true"
          aria-label="Office deployment wizard"
          onClick={(event) => event.stopPropagation()}
        >
          <header className="stg-recovery-wizard__header">
            <div>
              <h2><Server size={18} aria-hidden /> Office deployment wizard</h2>
              <p className="stg-muted">
                Detect server environment, apply recommended paths, and generate a deployment summary — no config file editing.
              </p>
            </div>
            <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close">
              <X size={16} />
            </button>
          </header>

          <nav className="stg-recovery-wizard__steps" aria-label="Wizard steps">
            {WIZARD_STEPS.map((item) => (
              <span
                key={item.number}
                className={`stg-recovery-wizard__step${step >= item.number ? ' stg-recovery-wizard__step--active' : ''}`}
              >
                {item.number}. {item.label}
              </span>
            ))}
          </nav>

          <div className="stg-recovery-wizard__body">
            {error && <p className="stg-error">{error}</p>}

            {step === 1 && (
              <div className="stg-recovery-wizard__intro">
                <p>
                  This wizard detects network, PostgreSQL, Windows service, API, backup path, image storage,
                  AI provider, Tally, firewall, and ports. It saves recommended settings automatically and
                  produces a deployment summary for your records.
                </p>
                <ul className="stg-recovery-validation-list">
                  <li className="stg-recovery-status--healthy"><strong>No manual .env editing</strong><span>Paths and URLs are stored in WEBSTUDIO settings.</span></li>
                  <li className="stg-recovery-status--healthy"><strong>IP guidance</strong><span>Recommends Static IP or DHCP reservation for the server.</span></li>
                </ul>
                <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void runDetection()}>
                  {busy ? <RefreshCw size={14} className="spin" aria-hidden /> : <Network size={14} aria-hidden />}
                  Start detection
                </button>
              </div>
            )}

            {step >= 2 && detection && (
              <>
                <div className={`stg-recovery-banner ${statusClass(detection.overall_status)}`}>
                  <strong>Overall: {detection.overall_status}</strong>
                  <p className="stg-muted">
                    Server {detection.server_lan_ip} · {detection.hostname} · data root {detection.data_root}
                  </p>
                </div>

                <ul className="stg-recovery-validation-list">
                  {detection.checks.map((check) => (
                    <li key={check.key} className={statusClass(check.status)}>
                      <strong>{check.name}</strong>
                      <span>{check.message}</span>
                      {check.detail && <span className="stg-muted">{check.detail}</span>}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {step >= 3 && detection?.ip_strategy && (
              <div className="stg-recovery-issues">
                <h4 className="stg-subtitle">IP address recommendation</h4>
                <div className={`stg-recovery-banner ${statusClass('passed')}`}>
                  <strong>Recommended: {detection.ip_strategy.label}</strong>
                  <p>{detection.ip_strategy.rationale}</p>
                </div>
                <p className="stg-muted">
                  Alternative: {detection.ip_strategy.alternative} — {detection.ip_strategy.alternative_rationale}
                </p>
                {detection.recommendations.length > 0 && (
                  <>
                    <h4 className="stg-subtitle">Additional recommendations</h4>
                    <ul>
                      {detection.recommendations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {step === 4 && completeResult && (
              <div className="stg-recovery-issues">
                <h4 className="stg-subtitle">Deployment summary</h4>
                <div className="stg-readonly-grid">
                  <Readonly label="Company" value={completeResult.summary.company_name || '—'} />
                  <Readonly label="Status" value={completeResult.summary.overall_status} />
                  <Readonly label="Server LAN IP" value={completeResult.summary.server_lan_ip} />
                  <Readonly label="Client URL" value={completeResult.summary.client_connection_url ?? '—'} />
                  <Readonly label="Backup path" value={completeResult.summary.saved_configuration.backup_folder ?? '—'} />
                  <Readonly label="Image storage" value={completeResult.summary.saved_configuration.product_image_storage_path ?? '—'} />
                  <Readonly label="Completed" value={completeResult.completed_at} />
                </div>
                <p className="stg-muted">{completeResult.summary.administrator_note}</p>
                <button type="button" className="btn btn-ghost btn-sm" onClick={downloadSummary}>
                  <Download size={14} aria-hidden />
                  Download summary (JSON)
                </button>
              </div>
            )}
          </div>

          <footer className="stg-recovery-wizard__footer">
            {step > 1 && step < 4 && (
              <button type="button" className="btn btn-ghost" disabled={busy} onClick={() => setStep((s) => Math.max(1, s - 1))}>
                <ChevronLeft size={14} aria-hidden /> Back
              </button>
            )}
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              {step === 4 ? 'Close' : 'Cancel'}
            </button>
            {step === 2 && detection && (
              <button type="button" className="btn btn-primary" onClick={() => setStep(3)}>
                Continue <ChevronRight size={14} aria-hidden />
              </button>
            )}
            {step === 3 && (
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void finishDeployment()}>
                {busy ? <RefreshCw size={14} className="spin" aria-hidden /> : <Check size={14} aria-hidden />}
                Save &amp; finish
              </button>
            )}
            {step === 4 && (
              <button type="button" className="btn btn-primary" onClick={onClose}>Done</button>
            )}
          </footer>
        </div>
      </div>
    </ModalPortal>
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
