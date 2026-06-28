import type { ReactNode } from 'react';
import { Moon, Sun } from 'lucide-react';
import { breadcrumbTrail } from '../../config/navigation';
import type { WorkspaceRoute } from '../../config/navigation';
import { useNavigationStore, useSearchStore, useThemeStore } from '../../store';
import type { AuthSession } from '../../store/useAuthStore';
import type { ConnectionStatus } from './ConnectionBadge';
import type { TallyStatus } from './TallyStatusBadge';
import { Breadcrumb } from './Breadcrumb';
import { ConnectionBadge } from './ConnectionBadge';
import { NotificationBell } from './NotificationBell';
import { SearchBar } from './SearchBar';
import { TallyStatusBadge } from './TallyStatusBadge';
import { UserMenu } from './UserMenu';

interface TopToolbarProps {
  session: AuthSession;
  appVersion: string;
  connectionStatus: ConnectionStatus;
  tallyStatus: TallyStatus;
  showTallyStatus?: boolean;
  showNotifications?: boolean;
  notificationCount?: number;
  onLogout: () => void;
  onNotificationsClick?: () => void;
}

export function TopToolbar({
  session,
  appVersion,
  connectionStatus,
  tallyStatus,
  showTallyStatus = true,
  showNotifications = true,
  notificationCount = 0,
  onLogout,
  onNotificationsClick,
}: TopToolbarProps): JSX.Element {
  const { currentRoute, setRoute } = useNavigationStore();
  const { open: openSearch } = useSearchStore();
  const { resolvedTheme, toggleTheme } = useThemeStore();
  const crumbs = breadcrumbTrail(currentRoute);

  return (
    <header className="app-toolbar" role="banner">
      <div className="app-toolbar-start">
        <Breadcrumb
          items={crumbs}
          onNavigate={(route: WorkspaceRoute) => setRoute(route)}
        />
      </div>

      <div className="app-toolbar-center">
        <SearchBar onOpen={openSearch} />
      </div>

      <div className="app-toolbar-end">
        <ConnectionBadge status={connectionStatus} compact />
        {showTallyStatus && <TallyStatusBadge status={tallyStatus} compact />}
        {showNotifications && (
          <NotificationBell count={notificationCount} onClick={onNotificationsClick} />
        )}
        <button
          type="button"
          className="app-toolbar-icon-btn"
          onClick={() => void toggleTheme()}
          aria-label="Toggle theme"
          title="Toggle light/dark theme"
        >
          {resolvedTheme === 'dark' ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
        </button>
        <UserMenu session={session} appVersion={appVersion} onLogout={onLogout} />
        <span className="app-version-tag app-version-tag--hidden-sm" aria-label={`Application version ${appVersion}`}>
          v{appVersion}
        </span>
      </div>
    </header>
  );
}

interface PageContainerProps {
  children: ReactNode;
}

export function PageContainer({ children }: PageContainerProps): JSX.Element {
  return <div className="app-page-container animate-fade-in">{children}</div>;
}

interface PageHeaderProps {
  title: string;
  description: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps): JSX.Element {
  return (
    <header className="app-page-header">
      <div className="app-page-header-text">
        <h1 className="app-page-title">{title}</h1>
        <p className="app-page-description">{description}</p>
      </div>
      {actions && <div className="app-page-header-actions">{actions}</div>}
    </header>
  );
}
