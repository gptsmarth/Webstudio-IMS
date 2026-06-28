import { useEffect, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import type { TallySettingsGroup } from '../../services/api/SettingsService';
import { TallyService } from '../../services/api/TallyService';
import { Field, SaveButton, Section } from './settingsShared';

interface TallySettingsFormProps {
  tally: TallySettingsGroup;
  canWrite: boolean;
  saving?: boolean;
  onSave: (payload: TallySettingsGroup) => Promise<void>;
  onSaved?: () => Promise<void>;
  showStatus?: boolean;
  showManualSync?: boolean;
}

export function TallySettingsForm({
  tally,
  canWrite,
  saving = false,
  onSave,
  onSaved,
  showStatus = true,
  showManualSync = true,
}: TallySettingsFormProps): JSX.Element {
  const [form, setForm] = useState(tally);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => setForm(tally), [tally]);

  return (
    <Section title="Tally connection">
      {showStatus && (
        <div className="stg-readonly-grid">
          <div className="stg-readonly">
            <span className="stg-readonly__label">Connection status</span>
            <span className="stg-readonly__value">{form.connection_status}</span>
          </div>
          <div className="stg-readonly">
            <span className="stg-readonly__label">Last sync</span>
            <span className="stg-readonly__value">
              {form.last_sync_at ? formatDateTime(form.last_sync_at) : '—'}
            </span>
          </div>
          <div className="stg-readonly">
            <span className="stg-readonly__label">Next sync</span>
            <span className="stg-readonly__value">
              {form.next_sync_at ? formatDateTime(form.next_sync_at) : '—'}
            </span>
          </div>
          <div className="stg-readonly">
            <span className="stg-readonly__label">Companies</span>
            <span className="stg-readonly__value">
              {form.companies.length ? form.companies.join(', ') : 'None configured'}
            </span>
          </div>
        </div>
      )}

      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void onSave(form).then(() => onSaved?.());
        }}
      >
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.enabled}
            disabled={!canWrite}
            onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
          />
          Enable Tally integration
        </label>
        <Field label="Tally host (IP or hostname)">
          <input
            className="input"
            value={form.tally_host}
            disabled={!canWrite}
            placeholder="127.0.0.1"
            onChange={(e) => setForm({ ...form, tally_host: e.target.value })}
          />
        </Field>
        <Field label="Tally port">
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
          label="Sync interval (seconds)"
          hint="Ensure Tally ERP 9 is running with ODBC/XML gateway enabled on the host and port above."
        >
          <input
            className="input"
            type="number"
            min={300}
            value={form.sync_interval_seconds}
            disabled={!canWrite}
            onChange={(e) => setForm({ ...form, sync_interval_seconds: Number(e.target.value) })}
          />
        </Field>
        {canWrite && (
          <SaveButton label="Save Tally settings" saving={saving} canWrite={canWrite} />
        )}
      </form>

      {showManualSync && canWrite && (
        <div className="stg-actions">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={syncing}
            onClick={() =>
              void (async () => {
                setSyncing(true);
                try {
                  await TallyService.triggerSync();
                  await onSaved?.();
                } finally {
                  setSyncing(false);
                }
              })()
            }
          >
            <RefreshCw size={14} className={syncing ? 'stg-spin' : undefined} /> Manual sync
          </button>
        </div>
      )}
    </Section>
  );
}
