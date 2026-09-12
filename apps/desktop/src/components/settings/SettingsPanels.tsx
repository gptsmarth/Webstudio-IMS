import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Cloud, Database, Download, RefreshCw, Shield } from 'lucide-react';
import { formatDateTime, formatRelativeTime } from '../../lib/datetime';
import { auditSeverityBadgeClass, auditSeverityLabel } from '../../lib/audit';
import { formatBytes } from '../../lib/settings';
import { parseApiError } from '../../lib/apiError';
import {
  loadAppearancePreferences,
  saveAppearancePreferences,
  type AppearancePreferences,
} from '../../lib/settingsUi';
import type { SettingsWorkspaceState } from '../../hooks/useSettingsWorkspace';
import { useUiZoom } from '../../hooks/useUiZoom';
import {
  AuthenticationService,
  type SecurityDashboard,
} from '../../services/api/AuthenticationService';
import { ApiClientProvider } from '../../services/api/ApiClientProvider';
import {
  INTEGRATION_SERVICE_TYPES,
  IntegrationKeyService,
  type IntegrationKeySummary,
  type IntegrationServiceType,
} from '../../services/api/IntegrationKeyService';
import { VersionService } from '../../services/VersionService';
import { PlatformService, type PlatformVersionInfo } from '../../services/api/PlatformService';
import type {
  SettingsWorkspace,
  BackupSettingsUpdate,
  CloudBackupStatus,
} from '../../services/api/SettingsService';
import { SettingsService } from '../../services/api/SettingsService';
import {
  canExecuteRestore,
  canManageBackup,
  canViewRestore,
} from '../../services/PermissionService';
import { useAuthStore } from '../../store';
import { TallySettingsForm } from './TallySettingsForm';
import { RestoreWizard } from './RestoreWizard';
import { BackupAdminCenter } from './BackupAdminCenter';
import { DeploymentCenter } from './DeploymentCenter';
import { RecoveryCenter } from './RecoveryCenter';
import { OfficeDeploymentWizard } from './OfficeDeploymentWizard';
import { RecoveryWizard } from './RecoveryWizard';
import { NetworkAdminWizard } from './NetworkAdminWizard';
import type { Location } from '../../services/api/LocationService';
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
    <Section title="Company">
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
        <SaveButton
          label="Save general settings"
          saving={workspace.saving}
          canWrite={workspace.canWrite}
        />
      </form>
    </Section>
  );
}

export function SecurityPanel({ workspace, data }: PanelProps): JSX.Element {
  const [form, setForm] = useState(data.security);
  const [dashboard, setDashboard] = useState<SecurityDashboard | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);

  useEffect(() => setForm(data.security), [data.security]);

  const refreshDashboard = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError(null);
    try {
      setDashboard(await AuthenticationService.getSecurityDashboard());
    } catch {
      setDashboardError('Unable to load security dashboard.');
      setDashboard(null);
    } finally {
      setDashboardLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshDashboard();
  }, [refreshDashboard]);

  const unlockUser = async (userId: number) => {
    const client = await ApiClientProvider.getClient();
    await client.post(`/api/v1/users/${userId}/unlock`);
    await refreshDashboard();
  };

  const revokeSession = async (sessionId: number) => {
    await AuthenticationService.revokeSession(sessionId);
    await refreshDashboard();
  };

  const exportSecurityEvents = async (format: 'pdf' | 'xlsx') => {
    setExportLoading(true);
    try {
      await AuthenticationService.exportSecurityEvents(format);
    } finally {
      setExportLoading(false);
    }
  };

  return (
    <>
      <Section title="Security dashboard">
        <div className="stg-security-dashboard">
          {dashboardLoading && (
            <p className="stg-security-dashboard__hint">Loading security status…</p>
          )}
          {dashboardError && <p className="stg-security-dashboard__error">{dashboardError}</p>}
          {dashboard && (
            <>
              <div className="stg-readonly-grid">
                <Readonly
                  label="Your active sessions"
                  value={String(dashboard.active_session_count)}
                />
                <Readonly
                  label="Org-wide sessions"
                  value={String(dashboard.org_active_session_count)}
                />
                <Readonly label="Failed logins (24h)" value={String(dashboard.failed_logins_24h)} />
                <Readonly label="Locked accounts" value={String(dashboard.locked_users.length)} />
                <Readonly
                  label="Recovery key"
                  value={dashboard.recovery.configured ? 'Configured' : 'Not configured'}
                />
              </div>

              {dashboard.critical_alerts.length > 0 && (
                <div className="stg-security-dashboard__block">
                  <h3 className="stg-security-dashboard__subtitle">Critical alerts</h3>
                  <ul className="stg-security-dashboard__alerts">
                    {dashboard.critical_alerts.map((alert) => (
                      <li key={alert.id} className="stg-security-dashboard__alert-row">
                        <AlertTriangle size={16} aria-hidden />
                        <div>
                          <strong>
                            {alert.description ?? alert.security_event ?? 'Security alert'}
                          </strong>
                          <div className="stg-security-dashboard__meta">
                            {alert.actor_display_name ?? 'System'} ·{' '}
                            {formatRelativeTime(alert.created_at)}
                          </div>
                        </div>
                        <span className={auditSeverityBadgeClass(alert.severity)}>
                          {auditSeverityLabel(alert.severity)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="stg-security-dashboard__block">
                <h3 className="stg-security-dashboard__subtitle">Password policy</h3>
                <ul className="stg-security-dashboard__list">
                  {dashboard.password_policy.rules.map((rule) => (
                    <li key={rule}>{rule}</li>
                  ))}
                </ul>
              </div>

              {dashboard.locked_users.length > 0 && workspace.canWrite && (
                <div className="stg-security-dashboard__block">
                  <h3 className="stg-security-dashboard__subtitle">Locked users</h3>
                  <ul className="stg-security-dashboard__sessions">
                    {dashboard.locked_users.map((user) => (
                      <li key={user.id} className="stg-security-dashboard__session-row">
                        <span>{user.display_name || user.username}</span>
                        <span className="stg-security-dashboard__meta">
                          until {user.locked_until ? formatDateTime(user.locked_until) : '—'}
                        </span>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm"
                          onClick={() => void unlockUser(user.id)}
                        >
                          Unlock
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="stg-security-dashboard__block">
                <h3 className="stg-security-dashboard__subtitle">Your active sessions</h3>
                {dashboard.active_sessions.length === 0 ? (
                  <p className="stg-security-dashboard__hint">No active sessions.</p>
                ) : (
                  <ul className="stg-security-dashboard__sessions">
                    {dashboard.active_sessions.map((session) => (
                      <li key={session.id} className="stg-security-dashboard__session-row">
                        <span>
                          {session.device_label || 'Unknown device'}
                          {session.is_current ? ' (current)' : ''}
                        </span>
                        <span className="stg-security-dashboard__meta">
                          {session.ip_address ?? '—'}
                        </span>
                        {!session.is_current && (
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => void revokeSession(session.id)}
                          >
                            Revoke
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() =>
                    void AuthenticationService.logoutAll().then(() => refreshDashboard())
                  }
                >
                  Sign out all devices
                </button>
              </div>

              <div className="stg-security-dashboard__block">
                <h3 className="stg-security-dashboard__subtitle">Recent security events</h3>
                {dashboard.recent_security_events.length === 0 ? (
                  <p className="stg-security-dashboard__hint">No security events recorded yet.</p>
                ) : (
                  <ul className="stg-security-dashboard__sessions">
                    {dashboard.recent_security_events.slice(0, 12).map((event) => (
                      <li key={event.id} className="stg-security-dashboard__session-row">
                        <span>{event.description ?? event.security_event ?? 'Security event'}</span>
                        <span className={auditSeverityBadgeClass(event.severity)}>
                          {auditSeverityLabel(event.severity)}
                        </span>
                        <span className="stg-security-dashboard__meta">
                          {event.actor_display_name ?? 'System'} ·{' '}
                          {formatRelativeTime(event.created_at)}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="stg-security-dashboard__block">
                <h3 className="stg-security-dashboard__subtitle">Recent login activity</h3>
                <ul className="stg-security-dashboard__sessions">
                  {dashboard.recent_login_events.slice(0, 10).map((event) => (
                    <li key={event.id} className="stg-security-dashboard__session-row">
                      <span>{event.username}</span>
                      <span className={`badge ${event.success ? 'badge-success' : 'badge-danger'}`}>
                        {event.success ? 'Success' : 'Failed'}
                      </span>
                      <span className="stg-security-dashboard__meta">
                        {formatRelativeTime(event.created_at)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="stg-security-dashboard__export">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => void exportSecurityEvents('xlsx')}
                  disabled={exportLoading}
                >
                  <Download size={14} aria-hidden />
                  Export Excel
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => void exportSecurityEvents('pdf')}
                  disabled={exportLoading}
                >
                  <Download size={14} aria-hidden />
                  Export PDF
                </button>
              </div>
            </>
          )}
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void refreshDashboard()}
            disabled={dashboardLoading}
          >
            <RefreshCw size={14} aria-hidden />
            Refresh
          </button>
        </div>
      </Section>

      <Section title="Security policy">
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
              onChange={(e) =>
                setForm({ ...form, session_timeout_minutes: Number(e.target.value) })
              }
              disabled={!workspace.canWrite}
            />
          </Field>
          <Field label="Remember me session (days)">
            <input
              className="input"
              type="number"
              min={7}
              value={form.remember_me_ttl_days}
              onChange={(e) => setForm({ ...form, remember_me_ttl_days: Number(e.target.value) })}
              disabled={!workspace.canWrite}
            />
          </Field>
          <Field label="Minimum password length">
            <input
              className="input"
              type="number"
              min={8}
              value={form.password_min_length}
              onChange={(e) => setForm({ ...form, password_min_length: Number(e.target.value) })}
              disabled={!workspace.canWrite}
            />
          </Field>
          <Field label="Password history count">
            <input
              className="input"
              type="number"
              min={0}
              max={24}
              value={form.password_history_count}
              onChange={(e) => setForm({ ...form, password_history_count: Number(e.target.value) })}
              disabled={!workspace.canWrite}
            />
          </Field>
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.password_require_uppercase}
              onChange={(e) => setForm({ ...form, password_require_uppercase: e.target.checked })}
              disabled={!workspace.canWrite}
            />
            Require uppercase
          </label>
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.password_require_lowercase}
              onChange={(e) => setForm({ ...form, password_require_lowercase: e.target.checked })}
              disabled={!workspace.canWrite}
            />
            Require lowercase
          </label>
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.password_require_number}
              onChange={(e) => setForm({ ...form, password_require_number: e.target.checked })}
              disabled={!workspace.canWrite}
            />
            Require number
          </label>
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.password_require_symbol}
              onChange={(e) => setForm({ ...form, password_require_symbol: e.target.checked })}
              disabled={!workspace.canWrite}
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
              disabled={!workspace.canWrite}
            />
          </Field>
          <Field label="Lockout duration (minutes)">
            <input
              className="input"
              type="number"
              min={1}
              value={form.lockout_duration_minutes}
              onChange={(e) =>
                setForm({ ...form, lockout_duration_minutes: Number(e.target.value) })
              }
              disabled={!workspace.canWrite}
            />
          </Field>
          <div className="stg-readonly-grid">
            <Readonly
              label="JWT access TTL"
              value={`${form.jwt_access_token_ttl_minutes} minutes`}
            />
            <Readonly label="JWT refresh TTL" value={`${form.jwt_refresh_token_ttl_days} days`} />
            <Readonly label="JWT issuer" value={form.jwt_issuer} />
            <Readonly label="JWT audience" value={form.jwt_audience} />
            <Readonly
              label="Recovery key"
              value={form.recovery_key_configured ? 'Configured' : 'Not configured'}
            />
            <Readonly
              label="Recovery key last used"
              value={
                form.recovery_key_last_used_at
                  ? formatDateTime(form.recovery_key_last_used_at)
                  : '—'
              }
            />
            <Readonly
              label="HTTPS certificate"
              value={form.https_certificate_status.replaceAll('_', ' ')}
            />
          </div>
          <SaveButton
            label="Save security settings"
            saving={workspace.saving}
            canWrite={workspace.canWrite}
          />
        </form>
      </Section>
    </>
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
        <SaveButton
          label="Save inventory settings"
          saving={workspace.saving}
          canWrite={workspace.canWrite}
        />
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
        <SaveButton
          label="Save sales settings"
          saving={workspace.saving}
          canWrite={workspace.canWrite}
        />
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
  'gemini-2.5-flash-lite',
  'gemini-2.5-flash',
  'gemini-2.0-flash',
  'gemini-flash-lite-latest',
];

const OPENAI_MODELS = ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini', 'gpt-4.1'];

const AI_PROVIDERS = [
  { id: 'gemini', label: 'Google Gemini (recommended — live web search)' },
  { id: 'openai', label: 'OpenAI ChatGPT (knowledge + fallback)' },
] as const;

function providerStatusLabel(status: string): string {
  switch (status) {
    case 'healthy':
      return 'Healthy';
    case 'degraded':
      return 'Degraded';
    case 'unavailable':
      return 'Unavailable';
    case 'not_configured':
      return 'Not configured';
    default:
      return status;
  }
}

export function IntegrationsPanel({ workspace, data }: PanelProps): JSX.Element {
  const integrations = data.integrations;
  const geminiHealth = integrations.ai_provider_health.find((entry) => entry.provider === 'gemini');
  const openaiHealth = integrations.ai_provider_health.find((entry) => entry.provider === 'openai');
  const [form, setForm] = useState({
    gemini_model: integrations.gemini_model,
    openai_model: integrations.openai_model,
    ai_primary_provider: integrations.ai_primary_provider,
    ai_enrichment_enabled: integrations.ai_enrichment_enabled,
    ai_timeout_seconds: integrations.ai_timeout_seconds,
    ai_retry_count: integrations.ai_retry_count,
    asus_price_refresh_stale_days: integrations.asus_price_refresh_stale_days,
  });
  const [geminiApiKey, setGeminiApiKey] = useState('');
  const [openaiApiKey, setOpenaiApiKey] = useState('');
  const [clearGeminiKey, setClearGeminiKey] = useState(false);
  const [clearOpenaiKey, setClearOpenaiKey] = useState(false);
  const [testMessage, setTestMessage] = useState<string | null>(null);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);

  useEffect(() => {
    setForm({
      gemini_model: integrations.gemini_model,
      openai_model: integrations.openai_model,
      ai_primary_provider: integrations.ai_primary_provider,
      ai_enrichment_enabled: integrations.ai_enrichment_enabled,
      ai_timeout_seconds: integrations.ai_timeout_seconds,
      ai_retry_count: integrations.ai_retry_count,
      asus_price_refresh_stale_days: integrations.asus_price_refresh_stale_days,
    });
    setGeminiApiKey('');
    setOpenaiApiKey('');
    setClearGeminiKey(false);
    setClearOpenaiKey(false);
  }, [integrations]);

  const buildFallbackChain = (primary: string): string[] => {
    const ordered = primary === 'openai' ? ['openai', 'gemini'] : ['gemini', 'openai'];
    return ordered.filter((provider, index) => ordered.indexOf(provider) === index);
  };

  const handleTestProvider = async (provider: 'gemini' | 'openai') => {
    setTestingProvider(provider);
    setTestMessage(null);
    try {
      const result = await SettingsService.testAiProvider(provider);
      const latency = result.latency_ms != null ? ` (${result.latency_ms} ms)` : '';
      setTestMessage(`${result.message}${latency}`);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setTestMessage(message.message ?? `Could not test ${provider} connection.`);
    } finally {
      setTestingProvider(null);
    }
  };

  return (
    <>
      <IntegrationApiKeysSection />
      <Section title="AI product enrichment">
        <p className="stg-section__lead">
          Add Laptop auto-fetch uses your primary AI provider first, then falls back to the other if
          needed. Gemini searches the live web for exact SKUs (best for Indian model numbers).
          OpenAI ChatGPT fills gaps from training data. Product images are resolved separately via
          web search — never guessed by the model.
        </p>
        {geminiHealth && (
          <Readonly
            label="Gemini status"
            value={`${providerStatusLabel(geminiHealth.status)} · ${geminiHealth.requests} requests · ${geminiHealth.failures} failures · ${geminiHealth.rate_limits} rate limits`}
          />
        )}
        {openaiHealth && (
          <Readonly
            label="OpenAI status"
            value={`${providerStatusLabel(openaiHealth.status)} · ${openaiHealth.requests} requests · ${openaiHealth.failures} failures · ${openaiHealth.rate_limits} rate limits`}
          />
        )}
        <form
          className="stg-form"
          onSubmit={(e) => {
            e.preventDefault();
            const primary = form.ai_primary_provider;
            void workspace.saveIntegrations({
              gemini_model: form.gemini_model,
              openai_model: form.openai_model,
              gemini_api_key: geminiApiKey.trim() || null,
              openai_api_key: openaiApiKey.trim() || null,
              clear_gemini_api_key: clearGeminiKey,
              clear_openai_api_key: clearOpenaiKey,
              ai_primary_provider: primary,
              ai_fallback_chain: buildFallbackChain(primary),
              ai_enrichment_enabled: form.ai_enrichment_enabled,
              ai_timeout_seconds: form.ai_timeout_seconds,
              ai_retry_count: form.ai_retry_count,
              asus_price_refresh_stale_days: form.asus_price_refresh_stale_days,
            });
          }}
        >
          <label className="stg-check">
            <input
              type="checkbox"
              checked={form.ai_enrichment_enabled}
              disabled={!workspace.canWrite}
              onChange={(e) => setForm({ ...form, ai_enrichment_enabled: e.target.checked })}
            />
            Enable AI enrichment
          </label>
          <Field label="Primary provider">
            <select
              className="input"
              value={form.ai_primary_provider}
              disabled={!workspace.canWrite}
              onChange={(e) => setForm({ ...form, ai_primary_provider: e.target.value })}
            >
              {AI_PROVIDERS.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.label}
                </option>
              ))}
            </select>
          </Field>
          <Readonly
            label="Fallback order"
            value={buildFallbackChain(form.ai_primary_provider).join(' → ')}
          />
          <Field label="Timeout (seconds)">
            <input
              className="input"
              type="number"
              min={15}
              max={300}
              value={form.ai_timeout_seconds}
              disabled={!workspace.canWrite}
              onChange={(e) =>
                setForm({ ...form, ai_timeout_seconds: Number(e.target.value) || 90 })
              }
            />
          </Field>
          <Field
            label="Lookup attempts"
            hint="Total tries per spec lookup. Use 1 to conserve API quota; use 2 for one retry."
          >
            <input
              className="input"
              type="number"
              min={0}
              max={5}
              value={form.ai_retry_count}
              disabled={!workspace.canWrite}
              onChange={(e) => setForm({ ...form, ai_retry_count: Number(e.target.value) || 0 })}
            />
          </Field>
          <Field
            label="ASUS price refresh (days)"
            hint="How often ASUS stock prices auto-refresh via Gemini search. Raise this to spend less API quota; a new ASUS model or a manual 'Update prices' click always fetches immediately regardless of this setting."
          >
            <input
              className="input"
              type="number"
              min={1}
              max={90}
              value={form.asus_price_refresh_stale_days}
              disabled={!workspace.canWrite}
              onChange={(e) =>
                setForm({
                  ...form,
                  asus_price_refresh_stale_days: Number(e.target.value) || 30,
                })
              }
            />
          </Field>

          <h3 className="stg-subheading">Google Gemini API</h3>
          <Readonly
            label="Gemini API key status"
            value={
              integrations.gemini_configured
                ? `Configured (${integrations.gemini_api_key_hint ?? '••••'})`
                : 'Not configured'
            }
          />
          <Field label="Gemini model" hint="flash-lite is tried first when rate-limited.">
            <select
              className="input"
              value={form.gemini_model}
              onChange={(e) => setForm({ ...form, gemini_model: e.target.value })}
              disabled={!workspace.canWrite}
            >
              {GEMINI_MODELS.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Gemini API key"
            hint={
              integrations.gemini_configured
                ? 'Leave blank to keep the current key.'
                : 'Get a key at aistudio.google.com/apikey'
            }
          >
            <input
              className="input"
              type="password"
              autoComplete="off"
              placeholder={integrations.gemini_configured ? '••••••••••••' : 'AIza…'}
              value={geminiApiKey}
              disabled={!workspace.canWrite || clearGeminiKey}
              onChange={(e) => setGeminiApiKey(e.target.value)}
            />
          </Field>
          {integrations.gemini_configured && workspace.canWrite && (
            <label className="stg-check">
              <input
                type="checkbox"
                checked={clearGeminiKey}
                onChange={(e) => {
                  setClearGeminiKey(e.target.checked);
                  if (e.target.checked) setGeminiApiKey('');
                }}
              />
              Remove stored Gemini API key
            </label>
          )}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!workspace.canWrite || testingProvider !== null}
            onClick={() => void handleTestProvider('gemini')}
          >
            {testingProvider === 'gemini' ? 'Testing Gemini…' : 'Test Gemini connection'}
          </button>

          <h3 className="stg-subheading">OpenAI API (ChatGPT)</h3>
          <Readonly
            label="OpenAI API key status"
            value={
              integrations.openai_configured
                ? `Configured (${integrations.openai_api_key_hint ?? '••••'})`
                : 'Not configured'
            }
          />
          <Field label="OpenAI model" hint="gpt-4o-mini is the best cost/accuracy balance.">
            <select
              className="input"
              value={form.openai_model}
              onChange={(e) => setForm({ ...form, openai_model: e.target.value })}
              disabled={!workspace.canWrite}
            >
              {OPENAI_MODELS.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="OpenAI API key"
            hint={
              integrations.openai_configured
                ? 'Leave blank to keep the current key.'
                : 'Get a key at platform.openai.com/api-keys'
            }
          >
            <input
              className="input"
              type="password"
              autoComplete="off"
              placeholder={integrations.openai_configured ? '••••••••••••' : 'sk-…'}
              value={openaiApiKey}
              disabled={!workspace.canWrite || clearOpenaiKey}
              onChange={(e) => setOpenaiApiKey(e.target.value)}
            />
          </Field>
          {integrations.openai_configured && workspace.canWrite && (
            <label className="stg-check">
              <input
                type="checkbox"
                checked={clearOpenaiKey}
                onChange={(e) => {
                  setClearOpenaiKey(e.target.checked);
                  if (e.target.checked) setOpenaiApiKey('');
                }}
              />
              Remove stored OpenAI API key
            </label>
          )}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={!workspace.canWrite || testingProvider !== null}
            onClick={() => void handleTestProvider('openai')}
          >
            {testingProvider === 'openai' ? 'Testing OpenAI…' : 'Test OpenAI connection'}
          </button>

          {testMessage && <p className="stg-muted">{testMessage}</p>}
          <SaveButton
            label="Save AI settings"
            saving={workspace.saving}
            canWrite={workspace.canWrite}
          />
        </form>
      </Section>
    </>
  );
}

function IntegrationApiKeysSection(): JSX.Element | null {
  const session = useAuthStore((state) => state.session);
  const isMainAdmin = session?.role === 'main_admin';
  const [keys, setKeys] = useState<IntegrationKeySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceType, setServiceType] = useState<IntegrationServiceType>('email');
  const [label, setLabel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadKeys = useCallback(async () => {
    if (!isMainAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await IntegrationKeyService.listKeys(includeArchived);
      setKeys(rows);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load integration keys.');
      setKeys([]);
    } finally {
      setLoading(false);
    }
  }, [includeArchived, isMainAdmin]);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  if (!isMainAdmin) {
    return (
      <Section title="Integration API keys">
        <p className="stg-section__lead">
          Encrypted API keys for email, SMS, WhatsApp, and future services are managed by the Main
          Administrator.
        </p>
      </Section>
    );
  }

  return (
    <Section title="Integration API keys">
      <p className="stg-section__lead">
        Store encrypted credentials for outbound integrations. Keys are never shown in full after
        saving.
      </p>
      {error && <p className="stg-error">{error}</p>}
      <form
        className="stg-form"
        onSubmit={(e) => {
          e.preventDefault();
          void (async () => {
            setSaving(true);
            setError(null);
            try {
              await IntegrationKeyService.createKey({
                service_type: serviceType,
                label: label.trim(),
                api_key: apiKey.trim(),
              });
              setLabel('');
              setApiKey('');
              await loadKeys();
            } catch (err: unknown) {
              const message = err as { message?: string };
              setError(message.message ?? 'Unable to save integration key.');
            } finally {
              setSaving(false);
            }
          })();
        }}
      >
        <Field label="Service">
          <select
            className="input"
            value={serviceType}
            onChange={(e) => setServiceType(e.target.value as IntegrationServiceType)}
          >
            {INTEGRATION_SERVICE_TYPES.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Label">
          <input
            className="input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Production SMTP"
          />
        </Field>
        <Field label="API key">
          <input
            className="input"
            type="password"
            autoComplete="off"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Paste secret key"
          />
        </Field>
        <button type="submit" className="btn btn-primary btn-sm" disabled={saving}>
          {saving ? 'Saving…' : 'Add integration key'}
        </button>
      </form>
      <label className="stg-check">
        <input
          type="checkbox"
          checked={includeArchived}
          onChange={(e) => setIncludeArchived(e.target.checked)}
        />
        <span>Show archived keys</span>
      </label>
      {loading ? (
        <p className="stg-muted">Loading keys…</p>
      ) : keys.length === 0 ? (
        <p className="stg-muted">No integration keys configured yet.</p>
      ) : (
        <div className="stg-key-list">
          {keys.map((entry) => (
            <div key={entry.id} className="stg-key-card">
              <div>
                <strong>{entry.label}</strong>
                <p className="stg-muted">
                  {entry.service_type}
                  {entry.key_hint ? ` · ${entry.key_hint}` : ''}
                  {entry.is_archived ? ' · Archived' : ''}
                </p>
              </div>
              <div className="stg-key-card__actions">
                {!entry.is_archived ? (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() =>
                      void IntegrationKeyService.archiveKey(entry.id).then(() => loadKeys())
                    }
                  >
                    Archive
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() =>
                      void IntegrationKeyService.restoreKey(entry.id).then(() => loadKeys())
                    }
                  >
                    Restore
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
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
        <SaveButton
          label="Save Excel settings"
          saving={workspace.saving}
          canWrite={workspace.canWrite}
        />
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
        <label className="stg-check">
          <input
            type="checkbox"
            checked={form.backup_alerts_enabled}
            onChange={(e) => setForm({ ...form, backup_alerts_enabled: e.target.checked })}
          />
          Backup &amp; recovery alerts
        </label>
        <SaveButton
          label="Save notification settings"
          saving={workspace.saving}
          canWrite={workspace.canWrite}
        />
      </form>
    </Section>
  );
}

function GoogleDriveCloudBackupControls({ canManage }: { canManage: boolean }): JSX.Element {
  const [status, setStatus] = useState<CloudBackupStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retentionInput, setRetentionInput] = useState(25);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const result = await SettingsService.getCloudBackupStatus();
      setStatus(result);
      setRetentionInput(result.retention_count);
    } catch (err) {
      setError(parseApiError(err, 'Could not load Google Drive status.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setError(null);
    if (!window.cloudBackup) {
      setError('Google Drive connection is only available in the desktop app.');
      return;
    }
    setBusy(true);
    try {
      const oauthResult = await window.cloudBackup.connectGoogleDrive();
      const result = await SettingsService.connectGoogleDrive(oauthResult);
      setStatus(result);
      setRetentionInput(result.retention_count);
    } catch (err) {
      setError(parseApiError(err, 'Could not connect Google Drive.'));
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async () => {
    if (
      !window.confirm(
        'Disconnect Google Drive? Future backups will stop uploading to Drive. ' +
          'Existing local backups and backups already uploaded to Drive are not deleted.',
      )
    ) {
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const result = await SettingsService.disconnectGoogleDrive();
      setStatus(result);
    } catch (err) {
      setError(parseApiError(err, 'Could not disconnect Google Drive.'));
    } finally {
      setBusy(false);
    }
  };

  const handleRetentionSave = async () => {
    setError(null);
    setBusy(true);
    try {
      const result = await SettingsService.updateCloudBackupRetention(retentionInput);
      setStatus(result);
    } catch (err) {
      setError(parseApiError(err, 'Could not update retention count.'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <p className="stg-muted">Loading Google Drive status…</p>;
  }

  return (
    <div className="stg-cloud-backup">
      {error && <p className="stg-backup-error">{error}</p>}
      {status?.connected ? (
        <>
          <div className="stg-readonly-grid">
            <Readonly label="Connected account" value={status.account_email ?? '—'} />
            <Readonly
              label="Last sync"
              value={status.last_sync_at ? formatDateTime(status.last_sync_at) : 'Not synced yet'}
            />
            <Readonly label="Sync status" value={status.last_sync_status ?? 'pending'} />
          </div>
          {status.status === 'error' && status.last_error && (
            <p className="stg-backup-error">{status.last_error}</p>
          )}
          <div className="stg-form" style={{ maxWidth: 240 }}>
            <Field label="Keep most recent N backups on Drive">
              <input
                className="input"
                type="number"
                min={5}
                max={100}
                value={retentionInput}
                onChange={(e) => setRetentionInput(Number(e.target.value))}
                disabled={!canManage || busy}
              />
            </Field>
            {canManage && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={busy || retentionInput === status.retention_count}
                onClick={() => void handleRetentionSave()}
              >
                Save retention
              </button>
            )}
          </div>
          {canManage && (
            <div className="stg-actions">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={busy}
                onClick={() => void handleDisconnect()}
              >
                Disconnect
              </button>
            </div>
          )}
        </>
      ) : (
        canManage && (
          <div className="stg-actions">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy}
              onClick={() => void handleConnect()}
            >
              <Cloud size={14} aria-hidden />
              Connect Google Drive
            </button>
          </div>
        )
      )}
    </div>
  );
}

export function BackupPanel({ workspace, data }: PanelProps): JSX.Element {
  const permissions = useAuthStore((state) => state.session?.permissions ?? []);
  const canRunBackup = canManageBackup(permissions);
  const canOpenRestore = canViewRestore(permissions) || canExecuteRestore(permissions);
  const canRestoreActions = canExecuteRestore(permissions);
  const backup = data.backup;
  const [form, setForm] = useState<BackupSettingsUpdate>({
    backup_folder: backup.backup_folder,
    storage_backend: (backup.storage_backend as BackupSettingsUpdate['storage_backend']) || 'local',
    schedule: (backup.schedule as BackupSettingsUpdate['schedule']) || 'manual',
    retention_policy:
      (backup.retention_policy as BackupSettingsUpdate['retention_policy']) || 'last_30',
    retention_count: backup.retention_count,
  });
  const [lastResult, setLastResult] = useState<string | null>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [restoreFilename, setRestoreFilename] = useState<string | null>(null);
  const [recoveryWizardOpen, setRecoveryWizardOpen] = useState(false);
  const [networkWizardOpen, setNetworkWizardOpen] = useState(false);
  const [officeDeploymentOpen, setOfficeDeploymentOpen] = useState(false);

  useEffect(() => {
    setForm({
      backup_folder: backup.backup_folder,
      storage_backend:
        (backup.storage_backend as BackupSettingsUpdate['storage_backend']) || 'local',
      schedule: (backup.schedule as BackupSettingsUpdate['schedule']) || 'manual',
      retention_policy:
        (backup.retention_policy as BackupSettingsUpdate['retention_policy']) || 'last_30',
      retention_count: backup.retention_count,
    });
  }, [backup]);

  const healthClass =
    backup.health_status === 'healthy'
      ? 'stg-backup-health--healthy'
      : backup.health_status === 'degraded'
        ? 'stg-backup-health--degraded'
        : 'stg-backup-health--warning';

  const runBackup = async () => {
    setLastResult(null);
    try {
      const result = await SettingsService.createBackup({
        backup_type: 'full',
        trigger_type: 'manual',
      });
      const status = result.verification_status ?? 'success';
      setLastResult(
        `${status === 'success' ? 'Backup completed' : `Backup ${status}`}: ${result.filename} ` +
          `(${formatBytes(result.size_bytes)}, ${result.duration_ms ?? 0} ms)`,
      );
      await workspace.refresh();
    } catch (err) {
      setLastResult(parseApiError(err, 'Backup failed. Check server logs and storage location.'));
    }
  };

  return (
    <>
      <Section title="Backup dashboard">
        <div className={`stg-backup-health ${healthClass}`}>
          <Shield size={16} aria-hidden />
          <div>
            <strong>Health: {backup.health_status}</strong>
            <p className="stg-muted">
              Protects database, settings, users, integrations, and brand assets.
            </p>
          </div>
        </div>

        <p className="stg-backup-warning" role="note">
          Although automatic backups are maintained internally, it is recommended to create and
          safely store an external manual backup (weekly or monthly) so your business can be fully
          recovered even if the primary system or storage device fails.
        </p>

        <div className="stg-readonly-grid">
          <Readonly
            label="Last backup"
            value={backup.last_backup_at ? formatDateTime(backup.last_backup_at) : 'Never'}
          />
          <Readonly
            label="Next scheduled"
            value={
              backup.next_scheduled_backup_at
                ? formatDateTime(backup.next_scheduled_backup_at)
                : backup.schedule === 'manual'
                  ? 'Manual only'
                  : '—'
            }
          />
          <Readonly label="Database size" value={formatBytes(backup.database_size_bytes)} />
          <Readonly label="Retention policy" value={backup.retention_policy ?? 'last_30'} />
          <Readonly label="Storage location" value={backup.backup_folder} />
          <Readonly label="Storage backend" value={backup.storage_backend} />
        </div>

        {lastResult && <p className="stg-backup-result">{lastResult}</p>}

        {canRunBackup && (
          <div className="stg-actions">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={workspace.saving}
              onClick={() => void runBackup()}
            >
              <Database size={14} aria-hidden />
              Run manual backup
            </button>
            {canOpenRestore && (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={workspace.saving}
                onClick={() => {
                  setRestoreFilename(null);
                  setRestoreOpen(true);
                }}
              >
                <RefreshCw size={14} aria-hidden />
                Open Restore Center
              </button>
            )}
          </div>
        )}
      </Section>

      <Section title="Backup policy">
        <form
          className="stg-form"
          onSubmit={(e) => {
            e.preventDefault();
            void workspace.saveBackup(form);
          }}
        >
          <Field label="Local backup folder">
            <input
              className="input"
              value={form.backup_folder}
              onChange={(e) => setForm({ ...form, backup_folder: e.target.value })}
              disabled={!canRunBackup}
            />
          </Field>
          <Field label="Schedule">
            <select
              className="input"
              value={form.schedule}
              onChange={(e) =>
                setForm({
                  ...form,
                  schedule: e.target.value as BackupSettingsUpdate['schedule'],
                })
              }
              disabled={!canRunBackup}
            >
              <option value="manual">Manual</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </Field>
          <Field label="Retention policy">
            <select
              className="input"
              value={form.retention_policy}
              onChange={(e) =>
                setForm({
                  ...form,
                  retention_policy: e.target.value as BackupSettingsUpdate['retention_policy'],
                })
              }
              disabled={!canRunBackup}
            >
              <option value="last_7">Keep last 7</option>
              <option value="last_30">Keep last 30</option>
              <option value="last_90">Keep last 90</option>
              <option value="unlimited">Unlimited</option>
              <option value="custom">Custom count (future-ready)</option>
            </select>
          </Field>
          {form.retention_policy === 'custom' && (
            <Field label="Custom retention count">
              <input
                className="input"
                type="number"
                min={1}
                max={365}
                value={form.retention_count}
                onChange={(e) => setForm({ ...form, retention_count: Number(e.target.value) })}
                disabled={!canRunBackup}
              />
            </Field>
          )}
          <Field label="Storage backend">
            <select
              className="input"
              value={form.storage_backend}
              onChange={(e) =>
                setForm({
                  ...form,
                  storage_backend: e.target.value as BackupSettingsUpdate['storage_backend'],
                })
              }
              disabled={!canRunBackup}
            >
              <option value="local">Local folder</option>
              <option value="nas">NAS (future-ready)</option>
              <option value="external_drive">External drive (future-ready)</option>
              <option value="cloud">Cloud storage (future-ready)</option>
              <option value="google_drive">Google Drive</option>
            </select>
          </Field>
          {form.storage_backend === 'google_drive' && (
            <Field label="Google Drive">
              <GoogleDriveCloudBackupControls canManage={canRunBackup} />
            </Field>
          )}
          <SaveButton
            label="Save backup policy"
            saving={workspace.saving}
            canWrite={canRunBackup}
          />
        </form>
      </Section>

      <Section title="Recovery Center">
        <RecoveryCenter
          canManageBackup={canRunBackup}
          canViewRestore={canOpenRestore}
          canExecuteRestore={canRestoreActions}
          onOpenWizard={() => setRecoveryWizardOpen(true)}
          onOpenNetworkWizard={() => setNetworkWizardOpen(true)}
          onOpenOfficeDeploymentWizard={() => setOfficeDeploymentOpen(true)}
          onOpenRestore={() => {
            setRestoreFilename(null);
            setRestoreOpen(true);
          }}
          onRunBackup={runBackup}
        />
      </Section>

      <Section title="Backup administration">
        <BackupAdminCenter
          canManageBackup={canRunBackup}
          canExecuteRestore={canRestoreActions}
          onRestore={(filename) => {
            setRestoreFilename(filename);
            setRestoreOpen(true);
          }}
          onRefreshWorkspace={workspace.refresh}
        />
      </Section>

      {(backup.restore_history?.length ?? 0) > 0 && (
        <Section title="Recent restores">
          <div className="stg-backup-list">
            <ul>
              {backup.restore_history.map((item) => (
                <li key={item.id} className="stg-backup-row">
                  <div>
                    <span className="col-mono">{item.filename}</span>
                    <span className="stg-muted">
                      {item.restore_scope} · {item.source} · {formatDateTime(item.created_at)}
                    </span>
                    <span
                      className={`stg-backup-verify stg-backup-verify--${item.verification_status}`}
                    >
                      {item.verification_status}
                    </span>
                    {item.emergency_backup_filename && (
                      <span className="stg-muted col-mono">
                        Emergency: {item.emergency_backup_filename}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </Section>
      )}

      <RestoreWizard
        open={restoreOpen}
        backups={backup.history}
        initialFilename={restoreFilename}
        onClose={() => setRestoreOpen(false)}
        onComplete={workspace.refresh}
      />
      <RecoveryWizard
        open={recoveryWizardOpen}
        onClose={() => setRecoveryWizardOpen(false)}
        onOpenRestore={() => {
          setRecoveryWizardOpen(false);
          setRestoreFilename(null);
          setRestoreOpen(true);
        }}
        onRunBackup={runBackup}
        onComplete={workspace.refresh}
      />
      <NetworkAdminWizard open={networkWizardOpen} onClose={() => setNetworkWizardOpen(false)} />
      <OfficeDeploymentWizard
        open={officeDeploymentOpen}
        onClose={() => setOfficeDeploymentOpen(false)}
        onComplete={workspace.refresh}
      />
    </>
  );
}

export function AppearancePanel(): JSX.Element {
  const { theme, setTheme } = useThemeStore();
  const [appearance, setAppearance] = useState<AppearancePreferences>(loadAppearancePreferences());
  const {
    zoomFactor,
    zoomPercentLabel,
    zoomIn,
    zoomOut,
    resetZoom,
    setZoomFactor,
    available: zoomAvailable,
  } = useUiZoom();

  return (
    <Section title="Branding">
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
        {zoomAvailable && (
          <Field label="Display zoom">
            <div className="stg-zoom-controls">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void zoomOut()}
                disabled={zoomFactor <= 0.75}
              >
                Zoom out
              </button>
              <span className="stg-zoom-controls__value">{zoomPercentLabel}</span>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => void zoomIn()}
                disabled={zoomFactor >= 1.25}
              >
                Zoom in
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void resetZoom()}
              >
                Reset
              </button>
            </div>
            <input
              className="stg-zoom-controls__slider"
              type="range"
              min={75}
              max={125}
              step={5}
              value={Math.round(zoomFactor * 100)}
              onChange={(e) => void setZoomFactor(Number(e.target.value) / 100)}
              aria-label="Display zoom percent"
            />
            <p className="stg-field-hint">
              Scales the whole desktop UI (75%–125%). Use Zoom out on 14&quot; screens. Shortcuts:
              Ctrl+= / Ctrl+- / Ctrl+0.
            </p>
          </Field>
        )}
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

export function DeploymentPanel(): JSX.Element {
  const permissions = useAuthStore((state) => state.session?.permissions ?? []);
  const canModify = permissions.includes('settings:modify');
  return <DeploymentCenter canModify={canModify} />;
}

export function SystemPanel({ workspace, data }: PanelProps): JSX.Element {
  const sys = data.system;
  const [clientMeta, setClientMeta] = useState<Awaited<
    ReturnType<typeof VersionService.getVersionInfo>
  > | null>(null);

  useEffect(() => {
    void VersionService.getVersionInfo()
      .then(setClientMeta)
      .catch(() => setClientMeta(null));
  }, []);

  return (
    <Section title="System information">
      <div className="stg-health">
        <div
          className={`stg-health__card stg-health__card--${sys.api_health === 'ok' ? 'ok' : 'bad'}`}
        >
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
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={() => void workspace.refresh()}
      >
        <RefreshCw size={14} /> Refresh health
      </button>
    </Section>
  );
}

function formatReleaseChannel(channel: string | null | undefined): string {
  if (!channel) return '—';
  if (channel.toLowerCase() === 'beta') return 'Beta';
  if (channel.toLowerCase() === 'development') return 'Development';
  return 'Stable';
}

export function AboutPanel({ data }: { data: SettingsWorkspace }): JSX.Element {
  const [clientMeta, setClientMeta] = useState<Awaited<
    ReturnType<typeof VersionService.getVersionInfo>
  > | null>(null);
  const [serverVersion, setServerVersion] = useState<PlatformVersionInfo | null>(null);

  useEffect(() => {
    void VersionService.getVersionInfo()
      .then(setClientMeta)
      .catch(() => setClientMeta(null));
    void PlatformService.getVersion()
      .then(setServerVersion)
      .catch(() => setServerVersion(null));
  }, []);

  const version = clientMeta?.appVersion ?? serverVersion?.version ?? data.system.app_version;
  const buildNumber = clientMeta?.buildNumber ?? serverVersion?.build_number ?? '—';
  const gitCommit = clientMeta?.gitCommit ?? serverVersion?.git_commit ?? '—';
  const releaseDate = clientMeta?.buildDate ?? serverVersion?.release_date ?? '—';
  const releaseChannel = formatReleaseChannel(
    clientMeta?.releaseChannel ?? serverVersion?.release_channel,
  );
  const databaseRevision = serverVersion?.database_revision ?? '—';

  return (
    <Section title="Version & license">
      <div className="stg-about">
        <p>
          <strong>WEBSTUDIO IMS</strong> — Inventory Management System
        </p>
        <div className="stg-readonly-grid">
          <Readonly label="Version" value={version} />
          <Readonly label="Build number" value={String(buildNumber)} />
          <Readonly label="Git commit" value={gitCommit} />
          <Readonly label="Release date" value={releaseDate} />
          <Readonly label="Release channel" value={releaseChannel} />
          <Readonly label="Database revision" value={databaseRevision} />
        </div>
        <p className="stg-muted">Developed by WEBSTUDIO</p>
        <Readonly label="License" value="Not activated (enterprise licensing coming soon)" />
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
