import type { ReactNode } from 'react';

interface DashboardWidgetProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function DashboardWidget({
  title,
  subtitle,
  action,
  children,
  className = '',
}: DashboardWidgetProps): JSX.Element {
  return (
    <section className={`dash-widget ${className}`.trim()}>
      <header className="dash-widget__header">
        {(title || subtitle) && (
          <div>
            {title && <h2 className="dash-widget__title">{title}</h2>}
            {subtitle && <p className="dash-widget__subtitle">{subtitle}</p>}
          </div>
        )}
        {action}
      </header>
      <div className="dash-widget__body">{children}</div>
    </section>
  );
}

interface DashboardEmptyStateProps {
  title: string;
  description: string;
}

export function DashboardEmptyState({ title, description }: DashboardEmptyStateProps): JSX.Element {
  return (
    <div className="dash-empty">
      <p className="dash-empty__title">{title}</p>
      <p className="dash-empty__text">{description}</p>
    </div>
  );
}

export function DashboardSkeleton({ rows = 3 }: { rows?: number }): JSX.Element {
  return (
    <div className="dash-skeleton" aria-hidden>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="dash-skeleton__row skeleton" />
      ))}
    </div>
  );
}
