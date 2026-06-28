import type { WorkspaceRoute } from '../../config/navigation';
import { cn } from '../../lib/cn';

interface BreadcrumbProps {
  items: { label: string; route?: WorkspaceRoute }[];
  onNavigate?: (route: WorkspaceRoute) => void;
}

export function Breadcrumb({ items, onNavigate }: BreadcrumbProps): JSX.Element {
  return (
    <nav aria-label="Breadcrumb" className="app-breadcrumb">
      <ol className="app-breadcrumb-list">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`} className="app-breadcrumb-item">
              {index > 0 && <span className="app-breadcrumb-separator" aria-hidden>/</span>}
              {item.route && !isLast && onNavigate ? (
                <button
                  type="button"
                  className="app-breadcrumb-link"
                  onClick={() => onNavigate(item.route!)}
                >
                  {item.label}
                </button>
              ) : (
                <span className={cn('app-breadcrumb-text', isLast && 'app-breadcrumb-current')} aria-current={isLast ? 'page' : undefined}>
                  {item.label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
