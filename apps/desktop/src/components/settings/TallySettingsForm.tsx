import { useCallback, useEffect, useState } from 'react';
import { History, RefreshCw } from 'lucide-react';
import type { TallySettingsGroup } from '../../services/api/SettingsService';
import {
  TallyService,
  type TallyConnectionTestResult,
  type TallyOperationalSummary,
} from '../../services/api/TallyService';
import { Field, SaveButton, Section } from './settingsShared';
import { TallyOperationalMetrics, TallySyncHistoryPanel } from '../tally/TallySyncHistoryPanel';
import { formatPollingInterval } from '../../lib/tallyDisplay';

interface TallySettingsFormProps {
  tally: TallySettingsGroup;
  canWrite: boolean;
  saving?: boolean;
  onSave: (payload: TallySettingsGroup) => Promise<void>;
  onSaved?: () => Promise<void>;
}

export function TallySettingsForm({
  tally,
  canWrite,
  saving = false,
  onSave,
  onSaved,
}: TallySettingsFormProps): JSX.Element {
  const [form, setForm] = useState(tally);
  const [operational, setOperational] = useState<TallyOperationalSummary | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TallyConnectionTestResult | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [statusLoading, setStatusLoading] = useState(true);

  useEffect(() => setForm(tally), [tally]);

  const refreshStatus = useCallback(async (): Promise<TallyOperationalSummary | null> => {
    setStatusLoading(true);
    try {
      const dashboard = await TallyService.getDashboard();
      if (dashboard?.operational) {
        setOperational(dashboard.operational);
        return dashboard.operational;
      }
      return null;
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus, tally.enabled, tally.sync_interval_seconds]);

  const handleSaved = useCallback(async () => {
    await onSaved?.();
    await refreshStatus();
  }, [onSaved, refreshStatus]);

  return (
    <>
      <Section title="Tally synchronization">
        <p className="stg-section__lead">
          Connect WEBSTUDIO IMS to Tally for automatic sales import. Only business sync status is
          shown here.
        </p>

        {statusLoading && !operational ? (
          <div className="skeleton tally-ops-skeleton" />
        ) : operational ? (
          <TallyOperationalMetrics operational={operational} />
        ) : null}

        <div className="stg-actions tally-settings-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={testing}
            onClick={() =>
              void (async () => {
                setTesting(true);
                setTestError(null);
                try {
                  setTestResult(await TallyService.testConnection());
                } catch (err: unknown) {
                  const message = err as { message?: string };
                  setTestResult(null);
                  setTestError(message.message ?? 'Connection test failed.');
                } finally {
                  setTesting(false);
                }
              })()
            }
          >
            <RefreshCw size={14} className={testing ? 'stg-spin' : undefined} /> Test connection
          </button>
          {canWrite && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={syncing || !form.enabled}
              onClick={() =>
                void (async () => {
                  const previousSync = operational?.last_successful_sync_at ?? null;
                  setSyncing(true);
                  try {
                    await TallyService.triggerSync();
                    for (let attempt = 0; attempt < 12; attempt += 1) {
                      await new Promise((resolve) => setTimeout(resolve, 2500));
                      const latest = await refreshStatus();
                      if (
                        latest?.last_successful_sync_at &&
                        latest.last_successful_sync_at !== previousSync
                      ) {
                        break;
                      }
                      if (latest?.scheduler_status !== 'syncing') {
                        break;
                      }
                    }
                  } finally {
                    setSyncing(false);
                  }
                })()
              }
            >
              <RefreshCw size={14} className={syncing ? 'stg-spin' : undefined} /> Sync now
            </button>
          )}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setHistoryOpen(true)}
          >
            <History size={14} /> View sync history
          </button>
        </div>

        {testError && <p className="stg-form-error">{testError}</p>}
        {testResult && (
          <div className="tally-connection-result">
            <p className="tally-connection-result__summary">
              {testResult.reachable ? 'Connection successful' : 'Connection failed'} —{' '}
              {testResult.message}
            </p>
            {testResult.company_name && (
              <p className="tally-connection-result__detail">Company: {testResult.company_name}</p>
            )}
          </div>
        )}
      </Section>

      <Section title="Connection settings">
        <form
          className="stg-form"
          onSubmit={(e) => {
            e.preventDefault();
            void onSave(form).then(() => handleSaved());
          }}
        >
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.enabled}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            Enable automatic Tally synchronization
          </label>
          <Field
            label="Tally workstation address"
            hint="Hostname or IP of the PC running Tally with XML Server enabled."
          >
            <input
              className="input"
              value={form.tally_host}
              disabled={!canWrite}
              placeholder="LENOVO-TALLY.local"
              onChange={(e) => setForm({ ...form, tally_host: e.target.value })}
            />
          </Field>
          <Field label="Port" hint="Default Tally XML port is 9000.">
            <input
              className="input"
              value={form.tally_port}
              disabled={!canWrite}
              placeholder="9000"
              onChange={(e) => setForm({ ...form, tally_port: e.target.value })}
            />
          </Field>
          <Field label="Company name in Tally">
            <input
              className="input"
              value={form.tally_company_name}
              disabled={!canWrite}
              placeholder="WEBSTUDIO"
              onChange={(e) => setForm({ ...form, tally_company_name: e.target.value })}
            />
          </Field>
          <Field
            label="Polling interval"
            hint={`How often IMS checks Tally for new invoices (${formatPollingInterval(form.sync_interval_seconds)}).`}
          >
            <input
              className="input"
              type="number"
              min={60}
              max={3600}
              value={form.sync_interval_seconds}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, sync_interval_seconds: Number(e.target.value) })}
            />
          </Field>
          {canWrite && (
            <SaveButton label="Save connection settings" saving={saving} canWrite={canWrite} />
          )}
        </form>
      </Section>

      <TallySyncHistoryPanel open={historyOpen} onClose={() => setHistoryOpen(false)} />
    </>
  );
}
