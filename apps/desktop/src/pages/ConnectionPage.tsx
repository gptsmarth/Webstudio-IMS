import { useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowRight, CheckCircle2, RefreshCw, Server, Wifi } from 'lucide-react';
import type {
  ConnectionStageResult,
  DiscoveredServer,
  SavedServerRecord,
} from '@webstudio/shared-kernel';
import { normalizeServerUrl } from '@webstudio/shared-kernel';
import { StartupBrandPanel, StartupShellLayout } from '../components/startup';
import { ConfigService } from '../services/ConfigService';
import { ConnectionDiagnosticsService } from '../services/ConnectionDiagnosticsService';
import { discoverBestServer } from '../services/ConnectionReconnectService';
import { SavedServerStore } from '../services/SavedServerStore';

interface ConnectionPageProps {
  onConnected: (isDemoMode?: boolean) => void;
}

type DiscoveryState = 'searching' | 'found' | 'manual' | 'testing';

const DISCOVERY_MESSAGES = [
  'Searching your local network',
  'Looking for WEBSTUDIO Server',
  'Verifying API endpoint',
  'Almost ready',
];

function formatLastSeen(iso?: string): string {
  if (!iso) return 'Just now';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  return date.toLocaleString();
}

function DiagnosticsStages({ stages }: { stages: ConnectionStageResult[] }): JSX.Element | null {
  if (stages.length === 0) return null;
  return (
    <ul className="connection-card__diagnostics">
      {stages.map((stage) => (
        <li key={stage.stage} className={stage.success ? 'is-ok' : 'is-failed'}>
          <span>{stage.success ? '✓' : '✗'}</span>
          <span>{stage.label}</span>
          {!stage.success && (
            <span className="connection-card__diagnostic-detail">{stage.message}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

export function ConnectionPage({ onConnected }: ConnectionPageProps): JSX.Element {
  const [state, setState] = useState<DiscoveryState>('searching');
  const [messageIndex, setMessageIndex] = useState(0);
  const [manualUrl, setManualUrl] = useState('http://192.168.29.100:8000');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [diagnosticStages, setDiagnosticStages] = useState<ConnectionStageResult[]>([]);
  const [discoveredServers, setDiscoveredServers] = useState<DiscoveredServer[]>([]);
  const [savedServers, setSavedServers] = useState<SavedServerRecord[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const cancelled = useRef(false);

  const loadSavedServers = async () => {
    const servers = await SavedServerStore.list();
    setSavedServers(servers);
  };

  const skipToManualEntry = () => {
    cancelled.current = true;
    setState('manual');
    setErrorMessage(null);
    window.setTimeout(() => inputRef.current?.focus(), 50);
  };

  const connectToUrl = async (rawUrl: string) => {
    cancelled.current = true;
    setState('testing');
    setErrorMessage(null);
    setDiagnosticStages([]);
    try {
      const result = await ConnectionDiagnosticsService.testConnection(rawUrl);
      setDiagnosticStages(result.stages);
      if (!result.success) {
        setState('manual');
        setErrorMessage(result.errorMessage ?? 'Could not connect to this address.');
        setManualUrl(rawUrl);
        return;
      }
      await ConfigService.setApiBaseUrl(result.url);
      await SavedServerStore.save({
        url: result.url,
        companyName: result.companyName,
        friendlyName: result.companyName,
        backendVersion: result.backendVersion,
        hostname: result.url ? new URL(result.url).hostname : undefined,
        lastConnectedAt: new Date().toISOString(),
      });
      await loadSavedServers();
      setState('found');
      window.setTimeout(() => onConnected(), 600);
    } catch {
      setState('manual');
      setErrorMessage('Could not connect to this address. Check the URL and try again.');
    }
  };

  const startAutomatedDiscovery = async () => {
    cancelled.current = false;
    setState('searching');
    setErrorMessage(null);
    setDiagnosticStages([]);
    setDiscoveredServers([]);
    setMessageIndex(0);
    await loadSavedServers();

    const interval = window.setInterval(() => {
      setMessageIndex((index) => (index + 1) % DISCOVERY_MESSAGES.length);
    }, 1800);

    try {
      const env = await ConfigService.getEnvironment();
      const best = await discoverBestServer({ preferredUrl: env.apiBaseUrl });
      if (cancelled.current) {
        window.clearInterval(interval);
        return;
      }

      window.clearInterval(interval);

      if (best?.success) {
        setDiscoveredServers([
          {
            id: `auto-${best.url}`,
            serverName: best.companyName ?? 'WEBSTUDIO Server',
            companyName: best.companyName ?? 'WEBSTUDIO',
            backendVersion: best.backendVersion ?? 'unknown',
            apiVersion: '1.0',
            buildVersion: '',
            environment: 'local',
            port: Number(new URL(best.url).port || 8000),
            host: new URL(best.url).hostname,
            url: best.url,
            lastSeen: new Date().toISOString(),
            status: 'online',
          },
        ]);
        setManualUrl(best.url);
        await connectToUrl(best.url);
        return;
      }

      setState('manual');
      window.setTimeout(() => inputRef.current?.focus(), 50);
    } catch {
      window.clearInterval(interval);
      if (!cancelled.current) {
        setState('manual');
        window.setTimeout(() => inputRef.current?.focus(), 50);
      }
    }
  };

  useEffect(() => {
    void startAutomatedDiscovery();
    return () => {
      cancelled.current = true;
    };
  }, []);

  const handleManualSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!manualUrl.trim()) return;
    try {
      const formattedUrl = normalizeServerUrl(manualUrl);
      await connectToUrl(formattedUrl);
    } catch (error) {
      setState('manual');
      setErrorMessage(error instanceof Error ? error.message : 'Invalid server address.');
    }
  };

  const footerStatus =
    state === 'found'
      ? 'Connected'
      : state === 'searching'
        ? 'Scanning network'
        : 'Manual configuration';

  const showManualForm = state === 'searching' || state === 'manual' || state === 'testing';

  return (
    <StartupShellLayout
      brand={
        <StartupBrandPanel
          footerRight={
            state === 'searching' ? 'CONNECTING' : state === 'found' ? 'CONNECTED' : 'SETUP'
          }
        />
      }
    >
      <div className="connection-card animate-slide-in">
        <header className="connection-card__header">
          <h1 className="connection-card__title">Connect to Server</h1>
          <p className="connection-card__subtitle">
            WEBSTUDIO looks for your shop server automatically. You can also enter the address
            manually anytime.
          </p>
        </header>

        <div className="connection-card__body">
          {state === 'searching' && (
            <div className="connection-card__status connection-card__status--loading">
              <div className="connection-card__spinner" aria-hidden>
                <span className="connection-card__spinner-core" />
                <span className="connection-card__spinner-ring" />
              </div>
              <div className="connection-card__status-copy">
                <p className="connection-card__status-title">Searching automatically</p>
                <p className="connection-card__status-detail">
                  {DISCOVERY_MESSAGES[messageIndex]}…
                </p>
              </div>
            </div>
          )}

          {state === 'found' && (
            <div className="connection-card__status connection-card__status--success">
              <CheckCircle2 size={36} aria-hidden className="connection-card__success-icon" />
              <div className="connection-card__status-copy">
                <p className="connection-card__status-title">Server found</p>
                <p className="connection-card__status-detail">Establishing secure connection…</p>
              </div>
            </div>
          )}

          {discoveredServers.length > 0 && state !== 'searching' && state !== 'found' && (
            <div className="connection-card__discovered">
              <p className="connection-card__section-title">Discovered on your network</p>
              {discoveredServers.map((server) => (
                <div key={server.id} className="connection-card__discovered-row">
                  <div>
                    <p className="connection-card__discovered-company">{server.companyName}</p>
                    <p className="connection-card__discovered-meta">
                      {server.serverName} · v{server.backendVersion} · {server.status} · Last seen{' '}
                      {formatLastSeen(server.lastSeen)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={state === 'testing'}
                    onClick={() => void connectToUrl(server.url)}
                  >
                    Connect
                  </button>
                </div>
              ))}
            </div>
          )}

          {showManualForm && (
            <form
              className="connection-card__form"
              onSubmit={(event) => void handleManualSubmit(event)}
            >
              {state === 'manual' && discoveredServers.length === 0 && (
                <div className="connection-card__status connection-card__status--manual">
                  <div className="connection-card__manual-icon" aria-hidden>
                    <Server size={20} />
                  </div>
                  <div className="connection-card__status-copy">
                    <p className="connection-card__status-title">Manual connection</p>
                    <p className="connection-card__status-detail">
                      Enter your WEBSTUDIO Server address (for example http://192.168.29.100:8000)
                      or retry automatic discovery.
                    </p>
                  </div>
                </div>
              )}

              {state === 'searching' && (
                <p className="connection-card__hint" style={{ marginBottom: 12 }}>
                  Searching your Wi‑Fi automatically. You can connect manually anytime using the
                  address below.
                </p>
              )}

              {errorMessage && (
                <div className="alert alert-danger connection-card__alert">
                  <AlertCircle size={14} aria-hidden />
                  <span>{errorMessage}</span>
                </div>
              )}

              <DiagnosticsStages stages={diagnosticStages} />

              <div>
                <label htmlFor="server-url" className="form-label">
                  Server address
                </label>
                <input
                  ref={inputRef}
                  id="server-url"
                  type="text"
                  className="input"
                  placeholder="192.168.1.10, WEBSTUDIO-SERVER, or WEBSTUDIO-SERVER.local"
                  value={manualUrl}
                  onChange={(event) => setManualUrl(event.target.value)}
                  disabled={state === 'testing'}
                />
                <p className="connection-card__hint">
                  IPv4, hostname, or .local name (for example http://WEBSTUDIO-SERVER.local:8000).
                </p>
              </div>

              <div className="connection-card__actions">
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={state === 'testing' || !manualUrl.trim()}
                >
                  {state === 'testing' ? (
                    <>
                      <span className="connection-card__btn-spinner" aria-hidden />
                      Verifying…
                    </>
                  ) : (
                    <>
                      Connect to server
                      <ArrowRight size={14} aria-hidden />
                    </>
                  )}
                </button>

                {state === 'searching' && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={skipToManualEntry}
                  >
                    Stop searching — use manual address only
                  </button>
                )}

                {state !== 'searching' && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void startAutomatedDiscovery()}
                    disabled={state === 'testing'}
                  >
                    <RefreshCw size={12} aria-hidden />
                    Retry automatic discovery
                  </button>
                )}
              </div>
            </form>
          )}

          {savedServers.length > 0 && state !== 'searching' && state !== 'found' && (
            <div className="connection-card__saved">
              <p className="connection-card__section-title">Saved servers</p>
              {savedServers.map((server) => (
                <div key={server.url} className="connection-card__discovered-row">
                  <div>
                    <p className="connection-card__discovered-company">
                      {server.friendlyName ?? server.companyName ?? server.url}
                    </p>
                    <p className="connection-card__discovered-meta">
                      {server.url}
                      {server.backendVersion ? ` · v${server.backendVersion}` : ''}
                      {server.lastConnectedAt
                        ? ` · Last connected ${formatLastSeen(server.lastConnectedAt)}`
                        : ''}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    disabled={state === 'testing'}
                    onClick={() => void connectToUrl(server.url)}
                  >
                    Connect
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="connection-card__footer">
          <div className="connection-card__footer-status">
            <Wifi size={12} aria-hidden />
            <span>{footerStatus}</span>
          </div>
          <button
            type="button"
            className="connection-card__preview"
            onClick={() => onConnected(true)}
          >
            Preview mode
          </button>
        </footer>
      </div>
    </StartupShellLayout>
  );
}
