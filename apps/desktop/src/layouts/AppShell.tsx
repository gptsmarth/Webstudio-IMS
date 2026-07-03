import { useEffect, useRef, useState } from 'react';
import { NAV_GROUPS, navItemsForPermissions, type WorkspaceRoute } from '../config/navigation';
import { useSessionManager } from '../hooks/useSessionManager';
import { PermissionService, P } from '../services/PermissionService';
import { TallyService } from '../services/api/TallyService';
import { DeploymentService } from '../services/api/DeploymentService';
import { useAuthStore, useNavigationStore, useSearchStore } from '../store';
import { useNotificationCenter } from '../hooks/useNotificationCenter';
import { OfficeDeploymentWizard } from '../components/settings/OfficeDeploymentWizard';
import {
  GlobalSearch,
  Sidebar,
  SidebarItem,
  TopToolbar,
  type ConnectionStatus,
  type TallyStatus,
} from '../components/shell';
import { useGlobalSearchShortcut, WorkspaceContent } from './WorkspaceContent';

interface AppShellProps {
  companyName: string;
  appVersion: string;
  connectionStatus: ConnectionStatus;
  onLogout: () => void;
}

export function AppShell({
  companyName,
  appVersion,
  connectionStatus,
  onLogout,
}: AppShellProps): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const { currentRoute, setRoute } = useNavigationStore();
  const { open: openSearch } = useSearchStore();
  const [tallyStatus, setTallyStatus] = useState<TallyStatus>('unavailable');
  const { unreadCount: notificationCount } = useNotificationCenter();

  const [sessionTimeoutMinutes, setSessionTimeoutMinutes] = useState(15);
  const [officeDeploymentOpen, setOfficeDeploymentOpen] = useState(false);
  const officeDeploymentPrompted = useRef(false);

  useGlobalSearchShortcut(openSearch);

  useSessionManager({
    sessionTimeoutMinutes,
    onIdleLogout: onLogout,
    enabled: Boolean(session),
  });

  useEffect(() => {
    if (!session) return;
    void (async () => {
      try {
        const { ApiClientProvider } = await import('../services/api/ApiClientProvider');
        const client = await ApiClientProvider.getClient();
        const policy = await client.get<{ session_timeout_minutes: number }>(
          '/api/v1/auth/session-policy',
        );
        setSessionTimeoutMinutes(policy.session_timeout_minutes);
      } catch {
        setSessionTimeoutMinutes(15);
      }
    })();
  }, [session]);

  const permissions = session?.permissions ?? [];
  const permissionService = PermissionService.from(permissions);
  const canViewTally = permissionService.has(P.tally.viewStatus);
  const canViewNotifications = permissionService.has(P.notifications.view);
  const canRunOfficeDeployment = permissionService.hasAny(
    P.settings.view,
    P.dashboard.systemStatus,
  );

  useEffect(() => {
    if (!session || !canRunOfficeDeployment || officeDeploymentPrompted.current) return;
    officeDeploymentPrompted.current = true;
    void DeploymentService.getStatus()
      .then((status) => {
        if (!status.completed) {
          setOfficeDeploymentOpen(true);
        }
      })
      .catch(() => {
        /* deployment status optional on first login */
      });
  }, [session, canRunOfficeDeployment]);

  useEffect(() => {
    if (!canViewTally) return;
    let cancelled = false;
    void TallyService.getSyncStatus()
      .then((status) => {
        if (cancelled) return;
        setTallyStatus(
          status.connection_health === 'healthy'
            ? 'connected'
            : status.connection_status === 'disconnected'
              ? 'unavailable'
              : 'error',
        );
      })
      .catch(() => {
        if (!cancelled) setTallyStatus('unavailable');
      });
    return () => {
      cancelled = true;
    };
  }, [canViewTally]);

  if (!session) {
    return (
      <div className="app-shell-loading">
        <p>Loading session…</p>
      </div>
    );
  }

  const visibleNav = navItemsForPermissions(session.permissions);

  return (
    <div className="app-shell">
      <Sidebar companyName={companyName}>
        {NAV_GROUPS.map((group) => {
          const items = visibleNav.filter((item) => item.group === group.id);
          if (items.length === 0) return null;
          return (
            <div key={group.id} className="app-sidebar-group">
              <p className="app-sidebar-group-label">{group.label}</p>
              {items.map((item) => (
                <SidebarItem
                  key={item.id}
                  label={item.label}
                  icon={item.icon}
                  active={currentRoute === item.id}
                  onClick={() => setRoute(item.id as WorkspaceRoute)}
                />
              ))}
            </div>
          );
        })}
      </Sidebar>

      <div className="app-shell-main">
        <TopToolbar
          session={session}
          appVersion={appVersion}
          connectionStatus={connectionStatus}
          tallyStatus={canViewTally ? tallyStatus : 'unavailable'}
          showTallyStatus={canViewTally}
          showNotifications={canViewNotifications}
          notificationCount={canViewNotifications ? notificationCount : 0}
          onLogout={onLogout}
          onNotificationsClick={canViewNotifications ? () => setRoute('notifications') : undefined}
        />
        <main className="app-content" id="main-content" tabIndex={-1}>
          <WorkspaceContent />
        </main>
      </div>

      <GlobalSearch />

      {canRunOfficeDeployment && (
        <OfficeDeploymentWizard
          open={officeDeploymentOpen}
          onClose={() => setOfficeDeploymentOpen(false)}
        />
      )}
    </div>
  );
}
