import type { SalesWorkspaceState } from '../../hooks/useSalesWorkspace';

interface SalesStatusBarProps {
  workspace: Pick<
    SalesWorkspaceState,
    'totalItems' | 'items' | 'loading' | 'selectedId' | 'page' | 'pageSize'
  >;
}

export function SalesStatusBar({ workspace }: SalesStatusBarProps): JSX.Element {
  const selected = workspace.items.find((item) => item.id === workspace.selectedId);

  return (
    <footer className="sales-status-bar" aria-label="Sales status">
      <span>{workspace.loading ? 'Loading sales…' : `${workspace.totalItems} total sales`}</span>
      <span className="sales-status-bar__divider" aria-hidden>
        ·
      </span>
      <span>
        Page {workspace.page} · {workspace.pageSize} per page
      </span>
      {selected && (
        <>
          <span className="sales-status-bar__divider" aria-hidden>
            ·
          </span>
          <span className="sales-status-bar__selected">Selected: {selected.invoice_number}</span>
        </>
      )}
    </footer>
  );
}
