import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react';
import { formatInventoryDate } from '../../lib/inventory';
import { saleStatusBadgeClass, saleStatusLabel } from '../../lib/inventoryDomain';
import { hasActiveInventoryFilters } from '../../lib/inventoryExport';
import type {
  InventorySortField,
  InventoryWorkspaceState,
} from '../../hooks/useInventoryWorkspace';
import type { InventoryItemDetail } from '../../services/api/InventoryService';
import { InventoryBrandCell } from './InventoryBrandCell';
import { InventoryEmptyState } from './InventoryEmptyState';
import { InventoryRowActionsMenu, type RowAction } from './InventoryRowActionsMenu';
import { InventoryStatusBadge } from './InventoryStatusBadge';

interface ColumnDef {
  id: string;
  label: string;
  sortField?: InventorySortField;
  minWidth: number;
  defaultWidth: number;
}

const COLUMNS: ColumnDef[] = [
  { id: 'status', label: 'Status', sortField: 'status', minWidth: 100, defaultWidth: 110 },
  {
    id: 'serial',
    label: 'Serial Number',
    sortField: 'serial_number',
    minWidth: 140,
    defaultWidth: 160,
  },
  { id: 'brand', label: 'Brand', minWidth: 120, defaultWidth: 130 },
  { id: 'model', label: 'Product Model', minWidth: 150, defaultWidth: 170 },
  { id: 'color', label: 'Unit Color', sortField: 'color', minWidth: 90, defaultWidth: 100 },
  { id: 'location', label: 'Location', minWidth: 120, defaultWidth: 140 },
  { id: 'sale', label: 'Sale Status', minWidth: 100, defaultWidth: 110 },
  { id: 'added', label: 'Date Added', sortField: 'created_at', minWidth: 120, defaultWidth: 130 },
  { id: 'actions', label: '', minWidth: 48, defaultWidth: 48 },
];

const WIDTH_STORAGE_KEY = 'webstudio.inventory.column-widths.v3';

function loadWidths(): Record<string, number> {
  try {
    const raw = localStorage.getItem(WIDTH_STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, number>;
  } catch {
    return {};
  }
}

function saveWidths(widths: Record<string, number>): void {
  try {
    localStorage.setItem(WIDTH_STORAGE_KEY, JSON.stringify(widths));
  } catch {
    // ignore
  }
}

interface InventoryTableProps {
  workspace: Pick<
    InventoryWorkspaceState,
    | 'items'
    | 'loading'
    | 'selectedId'
    | 'selectItem'
    | 'sortField'
    | 'sortDirection'
    | 'toggleSort'
    | 'page'
    | 'pageSize'
    | 'totalItems'
    | 'totalPages'
    | 'setPage'
    | 'filters'
    | 'search'
    | 'resetFilters'
  >;
  canWrite: boolean;
  canSell: boolean;
  onAdd?: () => void;
  onRowAction: (action: RowAction, item: InventoryItemDetail) => void;
}

export function InventoryTable({
  workspace,
  canWrite,
  canSell,
  onAdd,
  onRowAction,
}: InventoryTableProps): JSX.Element {
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    const saved = loadWidths();
    return Object.fromEntries(
      COLUMNS.map((column) => [column.id, saved[column.id] ?? column.defaultWidth]),
    );
  });
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [menuState, setMenuState] = useState<{ item: InventoryItemDetail; rect: DOMRect } | null>(
    null,
  );
  const resizeRef = useRef<{ columnId: string; startX: number; startWidth: number } | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());

  const hasFilters = hasActiveInventoryFilters(workspace.filters, workspace.search);

  const onResizeMove = useCallback((event: MouseEvent) => {
    const state = resizeRef.current;
    if (!state) return;
    const column = COLUMNS.find((entry) => entry.id === state.columnId);
    if (!column) return;
    const next = Math.max(column.minWidth, state.startWidth + (event.clientX - state.startX));
    setWidths((current) => ({ ...current, [state.columnId]: next }));
  }, []);

  const onResizeEnd = useCallback(() => {
    resizeRef.current = null;
    window.removeEventListener('mousemove', onResizeMove);
    window.removeEventListener('mouseup', onResizeEnd);
  }, [onResizeMove]);

  useEffect(() => {
    saveWidths(widths);
  }, [widths]);

  useEffect(() => {
    setFocusedIndex(-1);
  }, [workspace.page, workspace.items]);

  useEffect(() => {
    if (focusedIndex < 0) return;
    rowRefs.current.get(focusedIndex)?.scrollIntoView({ block: 'nearest' });
  }, [focusedIndex]);

  const startResize = (columnId: string, event: React.MouseEvent) => {
    event.preventDefault();
    event.stopPropagation();
    resizeRef.current = { columnId, startX: event.clientX, startWidth: widths[columnId] ?? 120 };
    window.addEventListener('mousemove', onResizeMove);
    window.addEventListener('mouseup', onResizeEnd);
  };

  const renderSortIcon = (field?: InventorySortField) => {
    if (!field) return null;
    if (workspace.sortField !== field) {
      return <ArrowUpDown size={12} aria-hidden className="inv-sort-icon inv-sort-icon--idle" />;
    }
    return workspace.sortDirection === 'asc' ? (
      <ArrowUp size={12} aria-hidden className="inv-sort-icon" />
    ) : (
      <ArrowDown size={12} aria-hidden className="inv-sort-icon" />
    );
  };

  const onTableKeyDown = (event: React.KeyboardEvent) => {
    if (workspace.loading || workspace.items.length === 0) return;
    const lastIndex = workspace.items.length - 1;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setFocusedIndex((current) => Math.min(lastIndex, current < 0 ? 0 : current + 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setFocusedIndex((current) => Math.max(0, current < 0 ? 0 : current - 1));
    } else if (event.key === 'Enter' && focusedIndex >= 0) {
      event.preventDefault();
      workspace.selectItem(workspace.items[focusedIndex].id);
    } else if (event.key === 'Escape') {
      workspace.selectItem(null);
      setMenuState(null);
    }
  };

  const openRowMenu = (item: InventoryItemDetail, button: HTMLButtonElement) => {
    workspace.selectItem(item.id);
    setMenuState({ item, rect: button.getBoundingClientRect() });
  };

  const pageStart = workspace.totalItems === 0 ? 0 : (workspace.page - 1) * workspace.pageSize + 1;
  const pageEnd = Math.min(workspace.page * workspace.pageSize, workspace.totalItems);

  return (
    <div className="inv-table-shell">
      <div
        ref={scrollRef}
        className="inv-table-scroll"
        tabIndex={0}
        role="grid"
        aria-label="Inventory table"
        onKeyDown={onTableKeyDown}
      >
        <table className="table-root inv-table">
          <thead className="inv-table__head">
            <tr>
              {COLUMNS.map((column) => (
                <th
                  key={column.id}
                  style={{ width: widths[column.id], minWidth: column.minWidth }}
                  className={column.sortField ? 'inv-table__th-sortable' : undefined}
                  onClick={
                    column.sortField ? () => workspace.toggleSort(column.sortField!) : undefined
                  }
                >
                  <span className="inv-table__th-content">
                    {column.label}
                    {renderSortIcon(column.sortField)}
                  </span>
                  {column.id !== 'actions' && (
                    <span
                      className="inv-table__resize-handle"
                      onMouseDown={(event) => startResize(column.id, event)}
                      role="separator"
                      aria-orientation="vertical"
                      aria-label={`Resize ${column.label} column`}
                    />
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {workspace.loading &&
              Array.from({ length: 8 }).map((_, index) => (
                <tr key={`sk-${index}`} className="inv-table__row-skeleton">
                  {COLUMNS.map((column) => (
                    <td key={column.id}>
                      <div className="skeleton inv-table__skeleton" />
                    </td>
                  ))}
                </tr>
              ))}

            {!workspace.loading && workspace.items.length === 0 && (
              <tr className="inv-table__empty-row">
                <td colSpan={COLUMNS.length}>
                  <InventoryEmptyState
                    hasFilters={hasFilters}
                    onClearFilters={workspace.resetFilters}
                    onAdd={onAdd}
                    canWrite={canWrite}
                  />
                </td>
              </tr>
            )}

            {!workspace.loading &&
              workspace.items.map((item, index) => (
                <tr
                  key={item.id}
                  ref={(node) => {
                    if (node) rowRefs.current.set(index, node);
                    else rowRefs.current.delete(index);
                  }}
                  className={
                    [
                      workspace.selectedId === item.id ? 'selected' : '',
                      focusedIndex === index ? 'inv-table__row--focused' : '',
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined
                  }
                  onClick={() => workspace.selectItem(item.id)}
                  onMouseEnter={() => setFocusedIndex(index)}
                >
                  <td>
                    <InventoryStatusBadge item={item} />
                  </td>
                  <td className="col-mono">{item.serial_number}</td>
                  <td>
                    <InventoryBrandCell brandName={item.brand_name} />
                  </td>
                  <td>
                    <span className="inv-model-cell">
                      <span className="inv-model-number">{item.model_number}</span>
                      <span className="inv-model-name">{item.model_name}</span>
                    </span>
                  </td>
                  <td>{item.color}</td>
                  <td>{item.current_location_name}</td>
                  <td>
                    <span
                      className={`badge ${saleStatusBadgeClass(item.status, item.is_archived)}`}
                    >
                      {saleStatusLabel(item.status, item.is_archived)}
                    </span>
                  </td>
                  <td>{formatInventoryDate(item.created_at)}</td>
                  <td>
                    <button
                      type="button"
                      className="inv-row-action"
                      aria-label={`Actions for ${item.serial_number}`}
                      aria-haspopup="menu"
                      onClick={(event) => {
                        event.stopPropagation();
                        openRowMenu(item, event.currentTarget);
                      }}
                    >
                      <MoreHorizontal size={14} aria-hidden />
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      {menuState && (
        <InventoryRowActionsMenu
          item={menuState.item}
          canWrite={canWrite}
          canSell={canSell}
          anchorRect={menuState.rect}
          onClose={() => setMenuState(null)}
          onAction={(action, item) => {
            setMenuState(null);
            onRowAction(action, item);
          }}
        />
      )}

      <div className="inv-table-pagination">
        <span className="inv-table-pagination__meta">
          {workspace.totalItems > 0
            ? `${pageStart}–${pageEnd} of ${workspace.totalItems}`
            : '0 items'}
        </span>
        <div className="inv-table-pagination__controls">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={workspace.page <= 1 || workspace.loading}
            onClick={() => workspace.setPage(workspace.page - 1)}
          >
            Previous
          </button>
          <span className="inv-table-pagination__page">
            Page {workspace.page} / {Math.max(workspace.totalPages, 1)}
          </span>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={workspace.page >= workspace.totalPages || workspace.loading}
            onClick={() => workspace.setPage(workspace.page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
