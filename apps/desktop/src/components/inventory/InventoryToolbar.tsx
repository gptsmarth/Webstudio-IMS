import { Download, Layers, MapPin, Plus, RefreshCw, Search, ShoppingBag } from 'lucide-react';
import type { InventoryWorkspaceState } from '../../hooks/useInventoryWorkspace';

interface InventoryToolbarProps {
  workspace: Pick<
    InventoryWorkspaceState,
    | 'search'
    | 'setSearch'
    | 'refresh'
    | 'loading'
    | 'selectedItem'
    | 'exportInventory'
    | 'actionLoading'
  >;
  canWrite: boolean;
  canSell: boolean;
  onAddItem: () => void;
  onTransfer: () => void;
  onMarkSold: () => void;
  onBulkOperations?: () => void;
}

export function InventoryToolbar({
  workspace,
  canWrite,
  canSell,
  onAddItem,
  onTransfer,
  onMarkSold,
  onBulkOperations,
}: InventoryToolbarProps): JSX.Element {
  const selected = workspace.selectedItem;
  const canTransfer = Boolean(
    canWrite && selected && !selected.is_archived && selected.status !== 'sold',
  );
  const canMarkSoldAction = Boolean(
    canSell && selected && !selected.is_archived && selected.status !== 'sold',
  );

  return (
    <div className="inv-toolbar">
      <div className="inv-toolbar__search">
        <Search size={15} aria-hidden className="inv-toolbar__search-icon" />
        <input
          type="search"
          className="input inv-toolbar__search-input"
          placeholder="Search serial, model, brand, location, invoice, customer…"
          value={workspace.search}
          onChange={(event) => workspace.setSearch(event.target.value)}
          aria-label="Search inventory"
        />
      </div>

      <div className="inv-toolbar__actions">
        {canWrite && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAddItem}>
            <Plus size={14} aria-hidden />
            Add Laptop
          </button>
        )}
        {canWrite && onBulkOperations && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onBulkOperations}>
            <Layers size={14} aria-hidden />
            Bulk
          </button>
        )}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onTransfer}
          disabled={!canTransfer}
          title={
            canTransfer ? 'Transfer selected laptop' : 'Select an available laptop to transfer'
          }
        >
          <MapPin size={14} aria-hidden />
          Transfer
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onMarkSold}
          disabled={!canMarkSoldAction}
          title={
            canMarkSoldAction ? 'Mark selected laptop as sold' : 'Select a laptop to mark sold'
          }
        >
          <ShoppingBag size={14} aria-hidden />
          Mark Sold
        </button>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => void workspace.exportInventory('xlsx')}
          disabled={workspace.actionLoading}
        >
          <Download size={14} aria-hidden />
          Export
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => void workspace.refresh()}
          disabled={workspace.loading}
          aria-label="Refresh inventory"
        >
          <RefreshCw size={14} aria-hidden className={workspace.loading ? 'inv-spin' : undefined} />
        </button>
      </div>
    </div>
  );
}
