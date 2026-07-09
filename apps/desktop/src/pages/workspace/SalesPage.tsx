import { AlertCircle } from 'lucide-react';
import {
  SalesDetailDrawer,
  SalesFiltersPanel,
  SalesStatusBar,
  SalesTable,
  SalesToolbar,
} from '../../components/sales';
import { useSalesWorkspace } from '../../hooks/useSalesWorkspace';
import { canExportSales } from '../../lib/sales';
import { useAuthStore } from '../../store';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';

export function SalesPage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const workspace = useSalesWorkspace(session?.permissions ?? []);

  if (!session) {
    return (
      <div className="sales-page">
        <div className="sales-empty">
          <p className="sales-empty__title">Session unavailable</p>
          <p className="sales-empty__text">Sign in again to access sales.</p>
        </div>
      </div>
    );
  }

  const canExport = canExportSales(session.permissions);

  return (
    <div className="sales-page animate-fade-in">
      <header className="sales-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="sales-page__title">Sales</h1>
          <p className="sales-page__subtitle">Completed sales, invoices, and customer records.</p>
        </div>
      </header>

      <SalesToolbar workspace={workspace} canExport={canExport} />

      <SalesFiltersPanel
        filters={workspace.filters}
        setFilters={workspace.setFilters}
        resetFilters={workspace.resetFilters}
        brands={workspace.brands}
        locations={workspace.locations}
        salespeople={workspace.salespeople}
      />

      {workspace.error && (
        <div className="alert alert-danger sales-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{workspace.error}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => void workspace.refresh()}
          >
            Retry
          </button>
        </div>
      )}

      {workspace.actionError && (
        <div className="alert alert-danger sales-page__alert">
          <AlertCircle size={14} aria-hidden />
          <span>{workspace.actionError}</span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={workspace.clearActionError}
          >
            Dismiss
          </button>
        </div>
      )}

      <div
        className={`sales-page__body ${workspace.selectedId ? 'sales-page__body--drawer-open' : ''}`}
      >
        <SalesTable workspace={workspace} onView={(item) => workspace.selectItem(item.id)} />
        <SalesDetailDrawer workspace={workspace} />
      </div>

      <SalesStatusBar workspace={workspace} />
    </div>
  );
}
