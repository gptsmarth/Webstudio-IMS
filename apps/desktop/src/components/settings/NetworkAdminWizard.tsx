import { useEffect, useState } from 'react';
import { Check, Network, RefreshCw, X } from 'lucide-react';
import {
  SettingsService,
  type NetworkReport,
  type NetworkValidationResult,
} from '../../services/api/SettingsService';
import { ModalPortal } from '../ModalPortal';

interface NetworkAdminWizardProps {
  open: boolean;
  onClose: () => void;
}

function statusClass(status: string): string {
  if (status === 'passed') return 'stg-recovery-status--healthy';
  if (status === 'failed') return 'stg-recovery-status--critical';
  return 'stg-recovery-status--warning';
}

export function NetworkAdminWizard({ open, onClose }: NetworkAdminWizardProps): JSX.Element | null {
  const [validation, setValidation] = useState<NetworkValidationResult | null>(null);
  const [report, setReport] = useState<NetworkReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setValidation(null);
    setReport(null);
    setError(null);
  }, [open]);

  if (!open) return null;

  const runValidation = async () => {
    setBusy(true);
    setError(null);
    try {
      const [result, networkReport] = await Promise.all([
        SettingsService.runNetworkValidation(),
        SettingsService.getNetworkReport(),
      ]);
      setValidation(result);
      setReport(networkReport);
    } catch {
      setError('Network validation failed.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalPortal>
      <div className="stg-restore-overlay" role="presentation" onClick={onClose}>
        <div
          className="stg-recovery-wizard animate-slide-in"
          role="dialog"
          aria-modal="true"
          aria-label="Network administrator wizard"
          onClick={(event) => event.stopPropagation()}
        >
          <header className="stg-recovery-wizard__header">
            <div>
              <h2><Network size={18} aria-hidden /> Network administrator wizard</h2>
              <p className="stg-muted">
                Validate server, database, API, firewall, ports, AI, Tally, and backup folders for your office LAN.
              </p>
            </div>
            <button type="button" className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close">
              <X size={16} />
            </button>
          </header>

          <div className="stg-recovery-wizard__body">
            {error && <p className="stg-error">{error}</p>}

            {!validation && (
              <div className="stg-recovery-wizard__intro">
                <p>
                  Supports static IP, DHCP reservation, multiple Wi‑Fi SSIDs and access points on the same LAN.
                  Tally laptop mobility is tolerated — no manual reconnect required for clients.
                </p>
                <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void runValidation()}>
                  {busy ? <RefreshCw size={14} className="spin" aria-hidden /> : <Check size={14} aria-hidden />}
                  Run validation
                </button>
              </div>
            )}

            {validation && (
              <>
                <div className={`stg-recovery-banner ${statusClass(validation.overall_status)}`}>
                  <strong>Overall: {validation.overall_status}</strong>
                  <p className="stg-muted">{validation.topology}</p>
                </div>

                <ul className="stg-recovery-validation-list">
                  {validation.checks.map((check) => (
                    <li key={check.key} className={statusClass(check.status)}>
                      <strong>{check.name}</strong>
                      <span>{check.message}</span>
                      {check.detail && <span className="stg-muted">{check.detail}</span>}
                    </li>
                  ))}
                </ul>

                {validation.recommendations.length > 0 && (
                  <div className="stg-recovery-issues">
                    <h4 className="stg-subtitle">Recommendations</h4>
                    <ul>
                      {validation.recommendations.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {report && (
                  <div className="stg-readonly-grid">
                    <Readonly label="Server LAN IP" value={report.server_lan_ip} />
                    <Readonly label="mDNS" value={report.mdns_active ? 'Active' : 'Inactive'} />
                    <Readonly label="API port" value={String(report.api_port)} />
                    <Readonly label="Data root" value={report.data_root} />
                  </div>
                )}
              </>
            )}
          </div>

          <footer className="stg-recovery-wizard__footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
            {validation && (
              <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void runValidation()}>
                Re-run validation
              </button>
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
