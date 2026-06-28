import { useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowRight, CheckCircle2, RefreshCw, Server, Wifi } from 'lucide-react';
import { StartupBrandPanel, StartupShellLayout } from '../components/startup';
import { SetupService } from '../services/api/SetupService';
import { ConfigService } from '../services/ConfigService';

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

const CANDIDATE_URLS = [
  'http://127.0.0.1:8000',
  'http://localhost:8000',
  'http://192.168.1.100:8000',
  'http://192.168.1.1:8000',
];

export function ConnectionPage({ onConnected }: ConnectionPageProps): JSX.Element {
  const [state, setState] = useState<DiscoveryState>('searching');
  const [messageIndex, setMessageIndex] = useState(0);
  const [manualUrl, setManualUrl] = useState('http://127.0.0.1:8000');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const cancelled = useRef(false);

  const startAutomatedDiscovery = async () => {
    cancelled.current = false;
    setState('searching');
    setErrorMessage(null);
    setMessageIndex(0);

    const interval = window.setInterval(() => {
      setMessageIndex((index) => (index + 1) % DISCOVERY_MESSAGES.length);
    }, 1800);

    for (const url of CANDIDATE_URLS) {
      if (cancelled.current) break;
      try {
        await ConfigService.setApiBaseUrl(url);
        await SetupService.getStatus();
        window.clearInterval(interval);
        if (!cancelled.current) {
          setState('found');
          window.setTimeout(() => {
            if (!cancelled.current) onConnected();
          }, 900);
        }
        return;
      } catch {
        // Try next URL
      }
    }

    window.clearInterval(interval);
    if (!cancelled.current) {
      setState('manual');
      window.setTimeout(() => inputRef.current?.focus(), 50);
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
    setState('testing');
    setErrorMessage(null);
    try {
      const formattedUrl = manualUrl.trim().replace(/\/$/, '');
      await ConfigService.setApiBaseUrl(formattedUrl);
      await SetupService.getStatus();
      setState('found');
      window.setTimeout(() => onConnected(), 600);
    } catch {
      setState('manual');
      setErrorMessage('Could not connect to this address. Check the URL and try again.');
    }
  };

  const footerStatus = state === 'found'
    ? 'Connected'
    : state === 'searching'
      ? 'Scanning network'
      : 'Manual configuration';

  return (
    <StartupShellLayout
      brand={(
        <StartupBrandPanel
          footerRight={state === 'searching' ? 'CONNECTING' : state === 'found' ? 'CONNECTED' : 'SETUP'}
        />
      )}
    >
      <div className="connection-card animate-slide-in">
        <header className="connection-card__header">
          <h1 className="connection-card__title">Connect to Server</h1>
          <p className="connection-card__subtitle">
            WEBSTUDIO IMS needs the local API server before setup or sign-in can begin.
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
                <p className="connection-card__status-title">Connecting to server</p>
                <p className="connection-card__status-detail">{DISCOVERY_MESSAGES[messageIndex]}…</p>
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

          {(state === 'manual' || state === 'testing') && (
            <form className="connection-card__form" onSubmit={(event) => void handleManualSubmit(event)}>
              <div className="connection-card__status connection-card__status--manual">
                <div className="connection-card__manual-icon" aria-hidden>
                  <Server size={20} />
                </div>
                <div className="connection-card__status-copy">
                  <p className="connection-card__status-title">Server not found</p>
                  <p className="connection-card__status-detail">
                    Enter your WEBSTUDIO Server address manually or retry automatic discovery.
                  </p>
                </div>
              </div>

              {errorMessage && (
                <div className="alert alert-danger connection-card__alert">
                  <AlertCircle size={14} aria-hidden />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div>
                <label htmlFor="server-url" className="form-label">Server address</label>
                <input
                  ref={inputRef}
                  id="server-url"
                  type="url"
                  className="input"
                  placeholder="http://192.168.1.x:8000"
                  value={manualUrl}
                  onChange={(event) => setManualUrl(event.target.value)}
                  disabled={state === 'testing'}
                />
                <p className="connection-card__hint">Ask your system administrator for the server URL.</p>
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

                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void startAutomatedDiscovery()}
                  disabled={state === 'testing'}
                >
                  <RefreshCw size={12} aria-hidden />
                  Retry automatic discovery
                </button>
              </div>
            </form>
          )}
        </div>

        <footer className="connection-card__footer">
          <div className="connection-card__footer-status">
            <Wifi size={12} aria-hidden />
            <span>{footerStatus}</span>
          </div>
          <button type="button" className="connection-card__preview" onClick={() => onConnected(true)}>
            Preview mode
          </button>
        </footer>
      </div>
    </StartupShellLayout>
  );
}
