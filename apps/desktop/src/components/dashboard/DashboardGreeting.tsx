import { formatDisplayDate, getTimeGreeting } from '../../lib/datetime';
import { formatRoleLabel } from '../../store/useAuthStore';
import type { AuthSession } from '../../store/useAuthStore';

interface DashboardGreetingProps {
  session: AuthSession;
}

export function DashboardGreeting({ session }: DashboardGreetingProps): JSX.Element {
  return (
    <header className="dash-greeting">
      <div>
        <p className="dash-greeting__time">{getTimeGreeting()}</p>
        <h1 className="dash-greeting__name">{session.displayName}</h1>
        <p className="dash-greeting__meta">
          <span>{formatRoleLabel(session.role)}</span>
          <span className="dash-greeting__dot" aria-hidden>·</span>
          <span>{formatDisplayDate()}</span>
        </p>
      </div>
    </header>
  );
}
