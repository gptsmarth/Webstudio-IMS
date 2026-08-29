import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, MoreHorizontal } from 'lucide-react';
import {
  canCancelSales,
  formatInvoiceDate,
  formatSaleAmount,
  saleSourceLabel,
  saleStatusBadgeClass,
  saleStatusLabel,
} from '../../lib/sales';
import { hasActiveSalesFilters } from '../../lib/salesExport';
import { canViewPurchasePrice } from '../../lib/inventory';
import { useAuthStore } from '../../store';
import { useHierarchyScrollRef } from '../../hooks/useHierarchyScrollRef';
import { useSalesScrollStore } from '../../store/useSalesScrollStore';
import type { SalesSortField, SalesWorkspaceState } from '../../hooks/useSalesWorkspace';
import type { SaleListItem } from '../../services/api/SalesService';
import { InventoryBrandCell } from '../inventory/InventoryBrandCell';
import { SalesEmptyState } from './SalesEmptyState';
import { SaleCancelDialog } from './SaleCancelDialog';
import { SalesRowActionsMenu } from './SalesRowActionsMenu';

interface ColumnDef {
  id: string;
  label: string;
  sortField?: SalesSortField;
  minWidth: number;
  defaultWidth: number;
}

const COLUMNS: ColumnDef[] = [
  {
    id: 'invoice',
    label: 'Invoice Number',
    sortField: 'invoice_number',
    minWidth: 130,
    defaultWidth: 150,
  },
  { id: 'date', label: 'Invoice Date', sortField: 'sold_at', minWidth: 120, defaultWidth: 130 },
  {
    id: 'customer',
    label: 'Customer',
    sortField: 'customer_name',
    minWidth: 140,
    defaultWidth: 160,
  },
  { id: 'brand', label: 'Brand', sortField: 'brand_name', minWidth: 120, defaultWidth: 130 },
  { id: 'model', label: 'Model', sortField: 'model_name', minWidth: 140, defaultWidth: 160 },
  {
    id: 'serial',
    label: 'Serial Number',
    sortField: 'serial_number',
    minWidth: 140,
    defaultWidth: 160,
  },
  { id: 'store', label: 'Store', sortField: 'location_name', minWidth: 120, defaultWidth: 140 },
  {
    id: 'payment',
    label: 'Payment Mode',
    sortField: 'payment_mode',
    minWidth: 110,
    defaultWidth: 120,
  },
  {
    id: 'source',
    label: 'Sale Source',
    sortField: 'sale_source',
    minWidth: 100,
    defaultWidth: 110,
  },
  { id: 'soldBy', label: 'Sold By', minWidth: 120, defaultWidth: 140 },
  { id: 'purchasePrice', label: 'Purchase Price', minWidth: 110, defaultWidth: 120 },
  { id: 'amount', label: 'Amount (incl. GST)', minWidth: 90, defaultWidth: 120 },
  { id: 'status', label: 'Status', minWidth: 100, defaultWidth: 110 },
  { id: 'actions', label: '', minWidth: 48, defaultWidth: 48 },
];

const WIDTH_STORAGE_KEY = 'webstudio.sales.column-widths';

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

interface SalesTableProps {
  workspace: Pick<
    SalesWorkspaceState,
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
    | 'cancelSale'
    | 'actionLoading'
  >;
  onView: (item: SaleListItem) => void;
}

export function SalesTable({ workspace, onView }: SalesTableProps): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const showPurchasePrice = session ? canViewPurchasePrice(session.permissions) : false;
  const canCancel = session ? canCancelSales(session.permissions) : false;
  const columns = showPurchasePrice
    ? COLUMNS
    : COLUMNS.filter((column) => column.id !== 'purchasePrice');
  const [widths, setWidths] = useState<Record<string, number>>(() => {
    const saved = loadWidths();
    return Object.fromEntries(
      columns.map((column) => [column.id, saved[column.id] ?? column.defaultWidth]),
    );
  });
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [menuState, setMenuState] = useState<{ item: SaleListItem; rect: DOMRect } | null>(null);
  const [cancelTarget, setCancelTarget] = useState<SaleListItem | null>(null);
  const resizeRef = useRef<{ columnId: string; startX: number; startWidth: number } | null>(null);
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());
  const getScrollTop = useSalesScrollStore((state) => state.getScrollTop);
  const setScrollTop = useSalesScrollStore((state) => state.setScrollTop);
  const { ref: scrollRef } = useHierarchyScrollRef(
    'sales-table',
    true,
    getScrollTop,
    setScrollTop,
    {
      ready: !workspace.loading,
    },
  );

  const hasFilters = hasActiveSalesFilters(workspace.filters, workspace.search);

  const onResizeMove = useCallback((event: MouseEvent) => {
    const state = resizeRef.current;
    if (!state) return;
    const column = columns.find((entry) => entry.id === state.columnId);
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

  const renderSortIcon = (field?: SalesSortField) => {
    if (!field) return null;
    if (workspace.sortField !== field) {
      return (
        <ArrowUpDown size={12} aria-hidden className="sales-sort-icon sales-sort-icon--idle" />
      );
    }
    return workspace.sortDirection === 'asc' ? (
      <ArrowUp size={12} aria-hidden className="sales-sort-icon" />
    ) : (
      <ArrowDown size={12} aria-hidden className="sales-sort-icon" />
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

  const pageStart = workspace.totalItems === 0 ? 0 : (workspace.page - 1) * workspace.pageSize + 1;
  const pageEnd = Math.min(workspace.page * workspace.pageSize, workspace.totalItems);

  return (
    <div className="sales-table-shell">
      <div
        ref={scrollRef}
        className="sales-table-scroll"
        tabIndex={0}
        role="grid"
        aria-label="Sales table"
        onKeyDown={onTableKeyDown}
      >
        <table className="table-root sales-table">
          <thead className="sales-table__head">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.id}
                  style={{ width: widths[column.id], minWidth: column.minWidth }}
                  className={column.sortField ? 'sales-table__th-sortable' : undefined}
                  onClick={
                    column.sortField ? () => workspace.toggleSort(column.sortField!) : undefined
                  }
                >
                  <span className="sales-table__th-content">
                    {column.label}
                    {renderSortIcon(column.sortField)}
                  </span>
                  {column.id !== 'actions' && (
                    <span
                      className="sales-table__resize-handle"
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
                <tr key={`sk-${index}`} className="sales-table__row-skeleton">
                  {columns.map((column) => (
                    <td key={column.id}>
                      <div className="skeleton sales-table__skeleton" />
                    </td>
                  ))}
                </tr>
              ))}

            {!workspace.loading && workspace.items.length === 0 && (
              <tr className="sales-table__empty-row">
                <td colSpan={columns.length}>
                  <SalesEmptyState
                    hasFilters={hasFilters}
                    onClearFilters={workspace.resetFilters}
                  />
                </td>
              </tr>
            )}

            {!workspace.loading &&
              workspace.items.map((sale, index) => (
                <tr
                  key={sale.id}
                  ref={(node) => {
                    if (node) rowRefs.current.set(index, node);
                    else rowRefs.current.delete(index);
                  }}
                  className={
                    [
                      workspace.selectedId === sale.id ? 'selected' : '',
                      focusedIndex === index ? 'sales-table__row--focused' : '',
                    ]
                      .filter(Boolean)
                      .join(' ') || undefined
                  }
                  onClick={() => workspace.selectItem(sale.id)}
                  onMouseEnter={() => setFocusedIndex(index)}
                >
                  <td>{sale.invoice_number}</td>
                  <td>{formatInvoiceDate(sale.sold_at)}</td>
                  <td>{sale.customer_name ?? '—'}</td>
                  <td>
                    <InventoryBrandCell brandName={sale.brand_name} />
                  </td>
                  <td>
                    <span className="sales-model-cell">
                      <span className="sales-model-number">{sale.model_number}</span>
                      <span className="sales-model-name">{sale.model_name}</span>
                    </span>
                  </td>
                  <td className="col-mono">{sale.serial_number}</td>
                  <td>{sale.location_name}</td>
                  <td>{sale.payment_mode ?? '—'}</td>
                  <td className="sales-table__source">{saleSourceLabel(sale.sale_source)}</td>
                  <td>{sale.recorded_by_display_name ?? '—'}</td>
                  {showPurchasePrice && (
                    <td className="sales-table__amount">{formatSaleAmount(sale.purchase_price)}</td>
                  )}
                  <td className="sales-table__amount">{formatSaleAmount(sale.sale_amount)}</td>
                  <td>
                    <span className={`badge ${saleStatusBadgeClass(sale.sale_source)}`}>
                      {saleStatusLabel(sale.sale_source)}
                    </span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="sales-row-action"
                      aria-label={`Actions for ${sale.invoice_number}`}
                      aria-haspopup="menu"
                      onClick={(event) => {
                        event.stopPropagation();
                        setMenuState({
                          item: sale,
                          rect: event.currentTarget.getBoundingClientRect(),
                        });
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
        <SalesRowActionsMenu
          item={menuState.item}
          canCancel={canCancel}
          anchorRect={menuState.rect}
          onClose={() => setMenuState(null)}
          onView={(item) => {
            setMenuState(null);
            onView(item);
          }}
          onDelete={(item) => {
            setMenuState(null);
            setCancelTarget(item);
          }}
        />
      )}

      <SaleCancelDialog
        open={cancelTarget !== null}
        sale={cancelTarget}
        loading={workspace.actionLoading}
        onClose={() => setCancelTarget(null)}
        onConfirm={async (reason) => {
          if (!cancelTarget) return;
          await workspace.cancelSale(cancelTarget.id, reason);
        }}
      />

      <div className="sales-table-pagination">
        <span className="sales-table-pagination__meta">
          {workspace.totalItems > 0
            ? `${pageStart}–${pageEnd} of ${workspace.totalItems}`
            : '0 sales'}
        </span>
        <div className="sales-table-pagination__controls">
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={workspace.page <= 1 || workspace.loading}
            onClick={() => workspace.setPage(workspace.page - 1)}
          >
            Previous
          </button>
          <span className="sales-table-pagination__page">
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
