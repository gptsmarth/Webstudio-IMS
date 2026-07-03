import { Download, RefreshCw, Search } from 'lucide-react';
import type { SalesWorkspaceState } from '../../hooks/useSalesWorkspace';

interface SalesToolbarProps {
  workspace: Pick<
    SalesWorkspaceState,
    'search' | 'setSearch' | 'refresh' | 'loading' | 'exportSales' | 'actionLoading'
  >;
  canExport: boolean;
}

export function SalesToolbar({ workspace, canExport }: SalesToolbarProps): JSX.Element {
  return (
    <div className="sales-toolbar">
      <div className="sales-toolbar__search">
        <Search size={15} aria-hidden className="sales-toolbar__search-icon" />
        <input
          type="search"
          className="input sales-toolbar__search-input"
          placeholder="Search invoice, customer, serial, brand, store…"
          value={workspace.search}
          onChange={(event) => workspace.setSearch(event.target.value)}
          aria-label="Search sales"
        />
      </div>

      <div className="sales-toolbar__actions">
        {canExport && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => void workspace.exportSales('xlsx')}
            disabled={workspace.actionLoading}
          >
            <Download size={14} aria-hidden />
            Export
          </button>
        )}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => void workspace.refresh()}
          disabled={workspace.loading}
          aria-label="Refresh sales"
        >
          <RefreshCw
            size={14}
            aria-hidden
            className={workspace.loading ? 'sales-spin' : undefined}
          />
        </button>
      </div>
    </div>
  );
}
