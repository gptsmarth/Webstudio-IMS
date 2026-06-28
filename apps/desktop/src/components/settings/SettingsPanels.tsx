import { useEffect, useState } from 'react';
import { AlertTriangle, Database, RefreshCw } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import { formatBytes } from '../../lib/settings';
import {
  loadAppearancePreferences,
  saveAppearancePreferences,
  type AppearancePreferences,
} from '../../lib/settingsUi';
import type { SettingsWorkspaceState } from '../../hooks/useSettingsWorkspace';
import { VersionService } from '../../services/VersionService';
import { TallySettingsForm } from './TallySettingsForm';
import type { Location } from '../../services/api/LocationService';
import type { SettingsWorkspace } from '../../services/api/SettingsService';
import { useThemeStore, type ThemeMode } from '../../store';
import { Field, Readonly, SaveButton, Section } from './settingsShared';

interface PanelProps {
  workspace: SettingsWorkspaceState;
  data: SettingsWorkspace;
  locations: Location[];
}

function StoreSelect({
  value,
  locations,
  onChange,
}: {
  value: number | null;
  locations: Location[];
  onChange: (id: number | null) => void;
}): JSX.Element {
  return (
    <select
      className="input"
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
    >
      <option value="">Not set</option>
      {locations.map((loc) => (
        <option key={loc.id} value={loc.id}>
          {loc.name}
        </option>
      ))}
    </select>
  );
}

export function GeneralPanel({ workspace, data, locations }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.general);
  useEffect(() => setForm(data.general), [data.general]);

  return (
    <Section title="General">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveGeneral(form);
        }}
      >
        <Field label="Company name">
          <input
            className="input"
            value={form.company_name}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
          />
        </Field>
        <Field label="Company logo" hint="Filename or URL (future-ready asset picker)">
          <input
            className="input"
            value={form.company_logo}
            onChange={(e) => setForm({ ...form, company_logo: e.target.value })}
          />
        </Field>
        <Field label="Address">
          <textarea
            className="input"
            rows={2}
            value={form.company_address}
            onChange={(e) => setForm({ ...form, company_address: e.target.value })}
          />
        </Field>
        <Field label="GST number">
          <input
            className="input"
            value={form.gst_number}
            onChange={(e) => setForm({ ...form, gst_number: e.target.value })}
          />
        </Field>
        <Field label="Phone">
          <input
            className="input"
            value={form.company_phone}
            onChange={(e) => setForm({ ...form, company_phone: e.target.value })}
          />
        </Field>
        <Field label="Email">
          <input
            className="input"
            type="email"
            value={form.company_email}
            onChange={(e) => setForm({ ...form, company_email: e.target.value })}
          />
        </Field>
        <Field label="Default store">
          <StoreSelect
            value={form.default_store_id}
            locations={locations}
            onChange={(id) => setForm({ ...form, default_store_id: id })}
          />
        </Field>
        <Field label="Default language" hint="Future-ready">
          <input className="input" value={form.default_language} disabled />
        </Field>
        <Field label="Timezone">
          <input
            className="input"
            value={form.timezone}
            onChange={(e) => setForm({ ...form, timezone: e.target.value })}
          />
        </Field>
        <Field label="Currency">
          <input
            className="input"
            value={form.currency}
            onChange={(e) => setForm({ ...form, currency: e.target.value })}
          />
        </Field>
        <SaveButton label="Save general settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function SecurityPanel({ workspace, data }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.security);
  useEffect(() => setForm(data.security), [data.security]);

  return (
    <Section title="Security">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveSecurity(form);
        }}
      >
        <Field label="Session timeout (minutes)">
          <input
            className="input"
            type="number"
            min={5}
            value={form.session_timeout_minutes}
            onChange={(e) => setForm({ ...form, session_timeout_minutes: Number(e.target.value) })}
          />
        </Field>
        <Field label="Minimum password length">
          <input
            className="input"
            type="number"
            min={8}
            value={form.password_min_length}
            onChange={(e) => setForm({ ...form, password_min_length: Number(e.target.value) })}
          />
        </Field>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.password_require_uppercase}
            onChange={(e) => setForm({ ...form, password_require_uppercase: e.target.checked })}
          />
          Require uppercase
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.password_require_number}
            onChange={(e) => setForm({ ...form, password_require_number: e.target.checked })}
          />
          Require number
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.password_require_symbol}
            onChange={(e) => setForm({ ...form, password_require_symbol: e.target.checked })}
          />
          Require symbol
        </label>
        <Field label="Login attempts before lockout">
          <input
            className="input"
            type="number"
            min={3}
            value={form.lockout_threshold}
            onChange={(e) => setForm({ ...form, lockout_threshold: Number(e.target.value) })}
          />
        </Field>
        <Field label="Lockout duration (minutes)">
          <input
            className="input"
            type="number"
            min={1}
            value={form.lockout_duration_minutes}
            onChange={(e) => setForm({ ...form, lockout_duration_minutes: Number(e.target.value) })}
          />
        </Field>
        <div className="stg-readonly-grid">
          <Readonly label="JWT access TTL" value={`${form.jwt_access_token_ttl_minutes} minutes`} />
          <Readonly label="JWT refresh TTL" value={`${form.jwt_refresh_token_ttl_days} days`} />
          <Readonly label="JWT issuer" value={form.jwt_issuer} />
          <Readonly label="JWT audience" value={form.jwt_audience} />
          <Readonly
            label="Recovery key"
            value={form.recovery_key_configured ? 'Configured' : 'Not configured'}
          />
          <Readonly
            label="Recovery key last used"
            value={form.recovery_key_last_used_at ? formatDateTime(form.recovery_key_last_used_at) : '—'}
          />
          <Readonly label="HTTPS certificate" value={form.https_certificate_status.replaceAll('_', ' ')} />
        </div>
        <SaveButton label="Save security settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function InventoryPanel({ workspace, data, locations }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.inventory);
  useEffect(() => setForm(data.inventory), [data.inventory]);

  return (
    <Section title="Inventory">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveInventory(form);
        }}
      >
        <Field label="Default inventory status">
          <select
            className="input"
            value={form.default_inventory_status}
            onChange={(e) => setForm({ ...form, default_inventory_status: e.target.value })}
          >
            <option value="received">Received</option>
            <option value="available">Available</option>
          </select>
        </Field>
        <Field label="Default store">
          <StoreSelect
            value={form.default_store_id}
            locations={locations}
            onChange={(id) => setForm({ ...form, default_store_id: id })}
          />
        </Field>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.qr_code_enabled}
            onChange={(e) => setForm({ ...form, qr_code_enabled: e.target.checked })}
          />
          Enable QR codes
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.auto_generate_labels}
            onChange={(e) => setForm({ ...form, auto_generate_labels: e.target.checked })}
          />
          Auto-generate labels
        </label>
        <Field label="Serial prefix">
          <input
            className="input"
            value={form.serial_number_prefix}
            onChange={(e) => setForm({ ...form, serial_number_prefix: e.target.value })}
          />
        </Field>
        <Field label="Serial suffix">
          <input
            className="input"
            value={form.serial_number_suffix}
            onChange={(e) => setForm({ ...form, serial_number_suffix: e.target.value })}
          />
        </Field>
        <Field label="Color configuration" hint="Comma-separated colors">
          <input
            className="input"
            value={form.inventory_colors.join(', ')}
            onChange={(e) =>
              setForm({
                ...form,
                inventory_colors: e.target.value
                  .split(',')
                  .map((v) => v.trim())
                  .filter(Boolean),
              })
            }
          />
        </Field>
        <SaveButton label="Save inventory settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function SalesPanel({ workspace, data }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.sales);
  useEffect(() => setForm(data.sales), [data.sales]);

  return (
    <Section title="Sales">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveSales(form);
        }}
      >
        <Field label="Default payment modes" hint="Comma-separated">
          <input
            className="input"
            value={form.default_payment_modes.join(', ')}
            onChange={(e) =>
              setForm({
                ...form,
                default_payment_modes: e.target.value
                  .split(',')
                  .map((v) => v.trim())
                  .filter(Boolean),
              })
            }
          />
        </Field>
        <Field label="Invoice prefix">
          <input
            className="input"
            value={form.invoice_prefix}
            onChange={(e) => setForm({ ...form, invoice_prefix: e.target.value })}
          />
        </Field>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.manual_sale_enabled}
            onChange={(e) => setForm({ ...form, manual_sale_enabled: e.target.checked })}
          />
          Allow manual sales
        </label>
        <Readonly label="Default salesperson" value="Not configured (future-ready)" />
        <SaveButton label="Save sales settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function TallyPanel({ workspace, data }: PanelProps): JSX.Element {
  return (
    <TallySettingsForm
      tally={data.tally}
      canWrite={workspace.canWrite}
      saving={workspace.saving}
      onSave={workspace.saveTally}
      onSaved={workspace.refresh}
    />
  );
}

const GEMINI_MODELS = [
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-2.0-flash',
  'gemini-flash-lite-latest',
];

export function IntegrationsPanel({ workspace, data }: PanelProps): JSX.Element {
  const [model, setModel] = useState(data.integrations.gemini_model);
  const [apiKey, setApiKey] = useState('');
  const [clearKey, setClearKey] = useState(false);

  useEffect(() => {
    setModel(data.integrations.gemini_model);
    setApiKey('');
    setClearKey(false);
  }, [data.integrations]);

  return (
    <Section title="Gemini AI">
      <p className="stg-section__lead">
        Powers Add Laptop auto-fetch for specifications and product images. Get a free API key from{' '}
        <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">
          Google AI Studio
        </a>
        .
      </p>
      <div className="stg-readonly-grid">
        <Readonly
          label="API key status"
          value={data.integrations.gemini_configured ? `Configured (${data.integrations.gemini_api_key_hint ?? '••••'})` : 'Not configured'}
        />
      </div>
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveIntegrations({
            gemini_model: model,
            gemini_api_key: apiKey.trim() || null,
            clear_gemini_api_key: clearKey,
          });
        }}
      >
        <Field label="Gemini model">
          <select className="input" value={model} onChange={(e) => setModel(e.target.value)} disabled={!workspace.canWrite}>
            {GEMINI_MODELS.map((entry) => (
              <option key={entry} value={entry}>{entry}</option>
            ))}
          </select>
        </Field>
        <Field
          label="Gemini API key"
          hint={
            data.integrations.gemini_configured
              ? 'Leave blank to keep the current key. Enter a new key to replace it.'
              : 'Paste your API key here. It is stored securely on the server and never shown again.'
          }
        >
          <input
            className="input"
            type="password"
            autoComplete="off"
            placeholder={data.integrations.gemini_configured ? '••••••••••••' : 'AIza…'}
            value={apiKey}
            disabled={!workspace.canWrite || clearKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </Field>
        {data.integrations.gemini_configured && workspace.canWrite && (
          <label className="stg-check">
            <input
              type="checkbox"
              checked={clearKey}
              onChange={(e) => {
                setClearKey(e.target.checked);
                if (e.target.checked) setApiKey('');
              }}
            />
            Remove stored API key
          </label>
        )}
        <SaveButton label="Save integration settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function ExcelPanel({ workspace, data }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.excel);
  useEffect(() => setForm(data.excel), [data.excel]);

  return (
    <Section title="Excel">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveExcel(form);
        }}
      >
        <Field label="Export folder">
          <input
            className="input"
            value={form.export_path}
            onChange={(e) => setForm({ ...form, export_path: e.target.value })}
          />
        </Field>
        <Field label="Default file naming">
          <input
            className="input"
            value={form.file_naming}
            onChange={(e) => setForm({ ...form, file_naming: e.target.value })}
          />
        </Field>
        <Readonly label="Auto export schedule" value="Not configured (future-ready)" />
        <SaveButton label="Save Excel settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function NotificationsPanel({ workspace, data }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.notifications);
  useEffect(() => setForm(data.notifications), [data.notifications]);

  return (
    <Section title="Notifications">
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void workspace.saveNotifications(form);
        }}
      >
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.notifications_enabled}
            onChange={(e) => setForm({ ...form, notifications_enabled: e.target.checked })}
          />
          Enable notifications
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.desktop_notifications}
            onChange={(e) => setForm({ ...form, desktop_notifications: e.target.checked })}
          />
          Desktop notifications
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.system_alerts_enabled}
            onChange={(e) => setForm({ ...form, system_alerts_enabled: e.target.checked })}
          />
          System alerts
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.tally_alerts_enabled}
            onChange={(e) => setForm({ ...form, tally_alerts_enabled: e.target.checked })}
          />
          Tally alerts
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.inventory_alerts_enabled}
            onChange={(e) => setForm({ ...form, inventory_alerts_enabled: e.target.checked })}
          />
          Inventory alerts
        </label>
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.audit_alerts_enabled}
            onChange={(e) => setForm({ ...form, audit_alerts_enabled: e.target.checked })}
          />
          Audit alerts
        </label>
        <SaveButton label="Save notification settings" saving={workspace.saving} canWrite={workspace.canWrite} />
      </form>
    </Section>
  );
}

export function BackupPanel({ workspace, data }: PanelProps): JSX.Element {
  const backup = data.backup;

  return (
    <Section title="Backup center">
      <div className="stg-readonly-grid">
        <Readonly label="Backup folder" value={backup.backup_folder} />
        <Readonly label="Database size" value={formatBytes(backup.database_size_bytes)} />
        <Readonly
          label="Last backup"
          value={backup.last_backup_at ? formatDateTime(backup.last_backup_at) : 'Never'}
        />
      </div>
      {workspace.canWrite && (
        <div className="stg-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={workspace.saving}
            onClick={() => void workspace.createBackup()}
          >
            <Database size={14} /> Create backup
          </button>
        </div>
      )}
      <div className="stg-backup-list">
        <h3 className="stg-subtitle">Backup history</h3>
        {backup.history.length === 0 && <p className="stg-muted">No backups found.</p>}
        <ul>
          {backup.history.map((item) => (
            <li key={item.filename} className="stg-backup-row">
              <div>
                <span className="col-mono">{item.filename}</span>
                <span className="stg-muted">
                  {formatBytes(item.size_bytes)} · {formatDateTime(item.created_at)}
                </span>
              </div>
              {workspace.canWrite && (
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  disabled={workspace.saving}
                  onClick={() => {
                    if (
                      window.confirm(
                        `Restore backup ${item.filename}? This will overwrite current data.`,
                      )
                    ) {
                      void workspace.restoreBackup(item.filename);
                    }
                  }}
                >
                  Restore
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
      <div className="stg-warning">
        <AlertTriangle size={14} />
        <span>Restore replaces live database content. Create a fresh backup before restoring.</span>
      </div>
    </Section>
  );
}

export function AppearancePanel(): JSX.Element {
  const { theme, setTheme } = useThemeStore();
  const [appearance, setAppearance] = useState<AppearancePreferences>(loadAppearancePreferences());

  return (
    <Section title="Appearance">
      <div className="stg-form">
        <Field label="Theme">
          <select
            className="input"
            value={theme}
            onChange={(e) => void setTheme(e.target.value as ThemeMode)}
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </Field>
        <Readonly label="Accent color" value="Default (future-ready)" />
        <label className="stg-check">
          <input
            type="checkbox"
            checked={appearance.compactMode}
            onChange={(e) => {
              const next = { ...appearance, compactMode: e.target.checked };
              setAppearance(next);
              saveAppearancePreferences(next);
            }}
          />
          Compact mode
        </label>
        <Field label="Table density">
          <select
            className="input"
            value={appearance.tableDensity}
            onChange={(e) => {
              const next = {
                ...appearance,
                tableDensity: e.target.value as AppearancePreferences['tableDensity'],
              };
              setAppearance(next);
              saveAppearancePreferences(next);
            }}
          >
            <option value="comfortable">Comfortable</option>
            <option value="compact">Compact</option>
          </select>
        </Field>
        <Field label="Sidebar behaviour">
          <select
            className="input"
            value={appearance.sidebarBehaviour}
            onChange={(e) => {
              const next = {
                ...appearance,
                sidebarBehaviour: e.target.value as AppearancePreferences['sidebarBehaviour'],
              };
              setAppearance(next);
              saveAppearancePreferences(next);
            }}
          >
            <option value="expanded">Expanded</option>
            <option value="collapsed">Collapsed</option>
          </select>
        </Field>
      </div>
    </Section>
  );
}

export function SystemPanel({ workspace, data }: PanelProps): JSX.Element {
  const sys = data.system;
  const [clientMeta, setClientMeta] = useState<Awaited<
    ReturnType<typeof VersionService.getVersionInfo>
  > | null>(null);

  useEffect(() => {
    void VersionService.getVersionInfo().then(setClientMeta).catch(() => setClientMeta(null));
  }, []);

  return (
    <Section title="System information">
      <div className="stg-health">
        <div className={`stg-health__card stg-health__card--${sys.api_health === 'ok' ? 'ok' : 'bad'}`}>
          <span>API health</span>
          <strong>{sys.api_health}</strong>
        </div>
        <div
          className={`stg-health__card stg-health__card--${sys.database_health === 'ok' ? 'ok' : 'bad'}`}
        >
          <span>Database</span>
          <strong>{sys.database_health}</strong>
        </div>
      </div>
      <div className="stg-readonly-grid">
        <Readonly label="Backend version" value={sys.app_version} />
        <Readonly label="API version" value={sys.api_version} />
        <Readonly label="Environment" value={sys.environment} />
        <Readonly label="Desktop version" value={clientMeta?.appVersion ?? '—'} />
        <Readonly label="Electron" value={clientMeta?.electronVersion ?? '—'} />
        <Readonly label="Node" value={clientMeta?.nodeVersion ?? '—'} />
        <Readonly label="Database version" value="PostgreSQL" />
        <Readonly label="Database size" value={formatBytes(sys.database_size_bytes)} />
        <Readonly label="Storage used" value={formatBytes(sys.storage_used_bytes)} />
        <Readonly label="Storage free" value={formatBytes(sys.storage_free_bytes)} />
        <Readonly label="Logs folder" value={sys.logs_folder} />
      </div>
      <button type="button" className="btn btn-ghost btn-sm" onClick={() => void workspace.refresh()}>
        <RefreshCw size={14} /> Refresh health
      </button>
    </Section>
  );
}

export function AboutPanel({ data }: { data: SettingsWorkspace }): JSX.Element {
  const [clientMeta, setClientMeta] = useState<Awaited<
    ReturnType<typeof VersionService.getVersionInfo>
  > | null>(null);

  useEffect(() => {
    void VersionService.getVersionInfo().then(setClientMeta).catch(() => setClientMeta(null));
  }, []);

  return (
    <Section title="About WEBSTUDIO IMS">
      <div className="stg-about">
        <p>
          <strong>WEBSTUDIO IMS</strong> — Inventory Management System
        </p>
        <p>Version {clientMeta?.appVersion ?? data.system.app_version}</p>
        <p className="stg-muted">Developed by WEBSTUDIO</p>
        <p className="stg-muted">License: Proprietary · Internal use</p>
        <h3 className="stg-subtitle">Credits</h3>
        <p className="stg-muted">
          Built for retail laptop inventory, sales, and Tally integration workflows.
        </p>
        <h3 className="stg-subtitle">Open source libraries</h3>
        <ul className="stg-libs">
          <li>React</li>
          <li>Zustand</li>
          <li>Lucide React</li>
          <li>Vite</li>
          <li>Electron</li>
          <li>Tailwind CSS</li>
        </ul>
      </div>
    </Section>
  );
}
