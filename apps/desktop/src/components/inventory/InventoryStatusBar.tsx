import type { InventoryWorkspaceState } from '../../hooks/useInventoryWorkspace';

interface InventoryStatusBarProps {
  workspace: Pick<InventoryWorkspaceState, 'totalItems' | 'items' | 'loading' | 'selectedId' | 'page' | 'pageSize'>;
  connectionLabel?: string;
}

export function InventoryStatusBar({ workspace, connectionLabel = 'Connected' }: InventoryStatusBarProps): JSX.Element {
  const selected = workspace.items.find((item) => item.id === workspace.selectedId);

  return (
    <footer className="inv-status-bar" aria-label="Inventory status">
      <span>{workspace.loading ? 'Loading inventory…' : `${workspace.totalItems} total items`}</span>
      <span className="inv-status-bar__divider" aria-hidden>
        ·
      </span>
      <span>
        Page {workspace.page} · {workspace.pageSize} per page
      </span>
      {selected && (
        <>
          <span className="inv-status-bar__divider" aria-hidden>
            ·
          </span>
          <span className="inv-status-bar__selected">
            Selected: <span className="col-mono">{selected.serial_number}</span>
          </span>
        </>
      )}
      <span className="inv-status-bar__spacer" />
      <span className="inv-status-bar__connection">{connectionLabel}</span>
    </footer>
  );
}
