import { useCallback, useEffect, useState } from 'react';
import { defaultRouteForPermissions, isRouteAllowedForPermissions } from './config/navigation';
import { useThemeStore, useAuthStore, useNavigationStore, type AuthSession } from './store';
import {
  VersionService,
  LoggingService,
  ConfigService,
  SetupService,
  AuthenticationService,
} from './services';
import { AuthTokenStore } from './services/AuthTokenStore';
import { sessionFromUser } from './store/useAuthStore';
import { SplashScreen, type StartupStage } from './components';
import { ConnectionPage, SetupWizardPage, LoginPage } from './pages';
import { AppShell } from './layouts/AppShell';
import type { ConnectionStatus } from './components/shell';
import {
  detectDatabaseReset,
  isSetupRequired,
  markLocalInitializedFlag,
  SETUP_REQUIRED_EVENT,
} from './lib/setupGuard';
import { initAppearancePreferences } from './lib/settingsUi';

interface AppVersionMeta {
  appVersion: string;
  buildVersion: string;
  gitCommit: string;
  buildDate: string;
  envMode: string;
  electronVersion: string;
  chromiumVersion: string;
  nodeVersion: string;
}

type AppView = 'connection' | 'setup' | 'login' | 'workspace';

export function App(): JSX.Element {
  const { initTheme } = useThemeStore();
  const { setSession, clearSession } = useAuthStore();
  const [bootStage, setBootStage] = useState<StartupStage>('initializing');
  const [activeView, setActiveView] = useState<AppView>('connection');
  const [companyName, setCompanyName] = useState<string>('WEBSTUDIO IMS');
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking');

  const [meta, setMeta] = useState<AppVersionMeta>({
    appVersion: '0.1.0',
    buildVersion: 'loading...',
    gitCommit: '...',
    buildDate: '...',
    envMode: 'development',
    electronVersion: '...',
    chromiumVersion: '...',
    nodeVersion: '...',
  });

  const evaluateServerState = useCallback(async () => {
    try {
      const status = await SetupService.getStatus();
      if (status.company_name) {
        setCompanyName(status.company_name);
      }
      setConnectionStatus('online');

      if (detectDatabaseReset(status)) {
        LoggingService.warn(
          'Renderer',
          'Database appears reset — local setup flag was set but server reports uninitialized',
        );
        await AuthTokenStore.clear();
        clearSession();
      }

      if (isSetupRequired(status)) {
        markLocalInitializedFlag(false);
        await AuthTokenStore.clear();
        clearSession();
        setActiveView('setup');
        return;
      }

      markLocalInitializedFlag(true);
      const restored = await AuthenticationService.restoreSession();
      if (restored) {
        setSession(sessionFromUser(restored));
        const permissions = restored.permissions ?? [];
        const { currentRoute, setRoute } = useNavigationStore.getState();
        if (!isRouteAllowedForPermissions(currentRoute, permissions)) {
          setRoute(defaultRouteForPermissions(permissions));
        }
        setActiveView('workspace');
        return;
      }
      setActiveView((current) => {
        if (current === 'connection' || current === 'setup') {
          return 'login';
        }
        return current;
      });
    } catch {
      setConnectionStatus('offline');
      setActiveView('connection');
    }
  }, [clearSession, setSession]);

  useEffect(() => {
    const onSetupRequired = () => {
      void (async () => {
        clearSession();
        await AuthTokenStore.clear();
        setActiveView('setup');
      })();
    };

    window.addEventListener(SETUP_REQUIRED_EVENT, onSetupRequired);
    return () => window.removeEventListener(SETUP_REQUIRED_EVENT, onSetupRequired);
  }, [clearSession]);

  useEffect(() => {
    if (activeView !== 'workspace') return;

    let cancelled = false;

    const poll = async () => {
      try {
        const { ApiClientProvider } = await import('./services/api/ApiClientProvider');
        const client = await ApiClientProvider.getClient();
        await client.getHealthLive();
        if (!cancelled) setConnectionStatus('online');
      } catch {
        if (!cancelled) {
          setConnectionStatus('offline');
          const { attemptAutomaticReconnect } =
            await import('./services/ConnectionReconnectService');
          const restored = await attemptAutomaticReconnect();
          if (restored && !cancelled) {
            setConnectionStatus('online');
            return;
          }
          void evaluateServerState();
        }
      }
    };

    void poll();
    const interval = setInterval(() => void poll(), 15_000);
    const onOnline = () => void poll();
    window.addEventListener('online', onOnline);

    return () => {
      cancelled = true;
      clearInterval(interval);
      window.removeEventListener('online', onOnline);
    };
  }, [activeView, evaluateServerState]);

  useEffect(() => {
    if (activeView !== 'workspace') return;

    let cancelled = false;
    void (async () => {
      const { startClientUpdatePolling } = await import('./services/UpdateCheckLifecycle');
      if (!cancelled) startClientUpdatePolling();
    })();

    return () => {
      cancelled = true;
      void import('./services/UpdateCheckLifecycle').then(({ stopClientUpdatePolling }) =>
        stopClientUpdatePolling(),
      );
    };
  }, [activeView]);

  useEffect(() => {
    const onFocus = () => {
      if (activeView === 'login' || activeView === 'workspace') {
        void evaluateServerState();
      }
    };

    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [activeView, evaluateServerState]);

  useEffect(() => {
    if (activeView !== 'login' && activeView !== 'setup') return;

    void evaluateServerState();
    const intervalMs = activeView === 'setup' ? 5_000 : 30_000;
    const interval = setInterval(() => void evaluateServerState(), intervalMs);
    return () => clearInterval(interval);
  }, [activeView, evaluateServerState]);

  useEffect(() => {
    void initTheme();
    initAppearancePreferences();
    LoggingService.info('Renderer', 'Application root mounted');

    async function bootstrap(): Promise<void> {
      const startedAt = Date.now();
      const MIN_SPLASH_MS = 1600;

      setBootStage('initializing');
      await new Promise((r) => setTimeout(r, 280));

      setBootStage('config');
      try {
        const vInfo = await VersionService.getVersionInfo();
        const envInfo = await ConfigService.getEnvironment();
        setMeta({
          appVersion: vInfo.appVersion,
          buildVersion: vInfo.buildVersion,
          gitCommit: vInfo.gitCommit,
          buildDate: vInfo.buildDate,
          envMode: envInfo.mode,
          electronVersion: vInfo.electronVersion,
          chromiumVersion: vInfo.chromiumVersion,
          nodeVersion: vInfo.nodeVersion,
        });
      } catch {
        LoggingService.warn('Renderer', 'Failed to retrieve version metadata');
      }
      await new Promise((r) => setTimeout(r, 320));

      setBootStage('preparing');
      try {
        if (window.api?.checkHealth) {
          const response = await window.api.checkHealth();
          setConnectionStatus(
            response.data?.status === 'online' || response.data?.status === 'ok'
              ? 'online'
              : 'offline',
          );
        } else {
          setConnectionStatus('offline');
        }
      } catch {
        setConnectionStatus('offline');
      }

      await evaluateServerState();
      await new Promise((r) => setTimeout(r, 280));

      const elapsed = Date.now() - startedAt;
      if (elapsed < MIN_SPLASH_MS) {
        await new Promise((r) => setTimeout(r, MIN_SPLASH_MS - elapsed));
      }

      setBootStage('ready');
    }

    void bootstrap();
  }, [initTheme]);

  const handleLoginSuccess = (session: AuthSession) => {
    markLocalInitializedFlag(true);
    setSession(session);
    useNavigationStore.getState().setRoute(defaultRouteForPermissions(session.permissions));
    setActiveView('workspace');
  };

  const handleSetupComplete = () => {
    markLocalInitializedFlag(true);
    void evaluateServerState();
  };

  const handleLogout = async () => {
    try {
      await AuthenticationService.logout();
    } catch {
      // Ignore network errors on logout
    }
    clearSession();
    setActiveView('login');
    void evaluateServerState();
  };

  if (bootStage !== 'ready') {
    return <SplashScreen stage={bootStage} appVersion={meta.appVersion} />;
  }

  if (activeView === 'connection') {
    return (
      <ConnectionPage
        onConnected={(demo?: boolean) => {
          if (demo) {
            setIsDemoMode(true);
            setConnectionStatus('offline');
            setActiveView('setup');
          } else {
            setIsDemoMode(false);
            void evaluateServerState();
          }
        }}
      />
    );
  }

  if (activeView === 'setup') {
    return (
      <SetupWizardPage
        isDemoMode={isDemoMode}
        appVersion={meta.appVersion}
        onSetupComplete={handleSetupComplete}
      />
    );
  }

  if (activeView === 'login') {
    return (
      <LoginPage
        companyName={companyName}
        apiUrl=""
        appVersion={meta.appVersion}
        onLoginSuccess={handleLoginSuccess}
        onSetupRequired={() => setActiveView('setup')}
      />
    );
  }

  return (
    <AppShell
      companyName={companyName}
      appVersion={meta.appVersion}
      connectionStatus={connectionStatus}
      onLogout={() => void handleLogout()}
    />
  );
}
