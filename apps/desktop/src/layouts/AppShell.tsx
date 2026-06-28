import { useEffect, useState } from 'react';
import { NAV_GROUPS, navItemsForRole, type WorkspaceRoute } from '../config/navigation';
import { TallyService } from '../services/api/TallyService';
import { useAuthStore, useNavigationStore, useSearchStore } from '../store';
import { useNotificationCenter } from '../hooks/useNotificationCenter';
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

export function AppShell({ companyName, appVersion, connectionStatus, onLogout }: AppShellProps): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const { currentRoute, setRoute } = useNavigationStore();
  const { open: openSearch } = useSearchStore();
  const [tallyStatus, setTallyStatus] = useState<TallyStatus>('unavailable');
  const { unreadCount: notificationCount } = useNotificationCenter();

  useGlobalSearchShortcut(openSearch);

  const isSalesperson = session?.role === 'salesperson';

  useEffect(() => {
    if (isSalesperson) return;
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
  }, [isSalesperson]);

  if (!session) {
    return (
      <div className="app-shell-loading">
        <p>Loading session…</p>
      </div>
    );
  }

  const visibleNav = navItemsForRole(session.role);

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
          tallyStatus={isSalesperson ? 'unavailable' : tallyStatus}
          showTallyStatus={!isSalesperson}
          showNotifications={!isSalesperson}
          notificationCount={isSalesperson ? 0 : notificationCount}
          onLogout={onLogout}
          onNotificationsClick={isSalesperson ? undefined : () => setRoute('notifications')}
        />
        <main className="app-content" id="main-content" tabIndex={-1}>
          <WorkspaceContent />
        </main>
      </div>

      <GlobalSearch />
    </div>
  );
}
