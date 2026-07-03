import { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, Monitor, Moon, Sun } from 'lucide-react';
import { useThemeStore } from '../../store';
import { formatRoleLabel, type AuthSession } from '../../store/useAuthStore';

interface UserMenuProps {
  session: AuthSession;
  appVersion: string;
  onLogout: () => void;
}

export function UserMenu({ session, appVersion, onLogout }: UserMenuProps): JSX.Element {
  const { theme, setTheme } = useThemeStore();
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const initials =
    session.displayName
      .split(/\s+/)
      .map((part) => part[0]?.toUpperCase() ?? '')
      .join('')
      .slice(0, 2) || session.username.slice(0, 2).toUpperCase();

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('mousedown', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  return (
    <div className="app-user-menu" ref={menuRef}>
      <button
        type="button"
        className="app-user-menu-trigger"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="User menu"
      >
        <span className="app-user-avatar" aria-hidden>
          {initials}
        </span>
        <span className="app-user-name">{session.displayName}</span>
        <ChevronDown size={14} aria-hidden style={{ color: 'var(--color-text-tertiary)' }} />
      </button>

      {open && (
        <div className="app-user-menu-panel animate-fade-in" role="menu">
          <div className="app-user-menu-header">
            <p className="app-user-menu-title">{session.displayName}</p>
            <p className="app-user-menu-subtitle">
              {formatRoleLabel(session.role)} · v{appVersion}
            </p>
          </div>
          <div className="divider" />
          <div className="app-user-menu-section" role="group" aria-label="Theme">
            <p className="app-user-menu-label">Theme</p>
            <div className="app-theme-options">
              {[
                { value: 'light' as const, label: 'Light', icon: Sun },
                { value: 'dark' as const, label: 'Dark', icon: Moon },
                { value: 'system' as const, label: 'System', icon: Monitor },
              ].map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  role="menuitemradio"
                  aria-checked={theme === value}
                  className={`app-theme-option${theme === value ? ' active' : ''}`}
                  onClick={() => void setTheme(value)}
                >
                  <Icon size={14} aria-hidden />
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="divider" />
          <button type="button" role="menuitem" className="app-user-menu-danger" onClick={onLogout}>
            <LogOut size={14} aria-hidden />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
