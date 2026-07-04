import type { ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '../../lib/cn';
import { WebstudioLogoImage } from '../branding/WebstudioLogoImage';

interface SidebarItemProps {
  label: string;
  icon: LucideIcon;
  active?: boolean;
  onClick: () => void;
}

export function SidebarItem({
  label,
  icon: Icon,
  active = false,
  onClick,
}: SidebarItemProps): JSX.Element {
  return (
    <button
      type="button"
      className={cn('nav-item w-full text-left', active && 'active')}
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
    >
      <Icon
        size={16}
        strokeWidth={active ? 2.25 : 1.75}
        style={{
          color: active ? 'var(--color-primary-500)' : 'var(--color-text-tertiary)',
          flexShrink: 0,
        }}
        aria-hidden
      />
      <span>{label}</span>
    </button>
  );
}

interface SidebarProps {
  companyName: string;
  children: ReactNode;
}

export function Sidebar({ companyName, children }: SidebarProps): JSX.Element {
  return (
    <aside className="app-sidebar" aria-label="Primary navigation">
      <div className="app-sidebar-header">
        <div className="app-sidebar-brand">
          <WebstudioLogoImage
            variant="auto"
            alt="WEBSTUDIO"
            className="app-sidebar-logo"
            fallbackText="WEBSTUDIO"
          />
        </div>
        <p className="app-sidebar-company" title={companyName}>
          {companyName}
        </p>
      </div>
      <nav className="app-sidebar-nav">{children}</nav>
    </aside>
  );
}
