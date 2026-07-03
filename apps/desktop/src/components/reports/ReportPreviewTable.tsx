import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import { formatDateTime } from '../../lib/datetime';
import type { useReportBuilder } from '../../hooks/useReportBuilder';
import type {
  AuditReportRow,
  BuilderReportType,
  InventoryReportRow,
  NotificationReportRow,
  SalesReportRow,
} from '../../services/api/ReportService';

type BuilderState = ReturnType<typeof useReportBuilder>;

interface ReportPreviewTableProps {
  reportType: BuilderReportType;
  rows: BuilderState['rows'];
  loading: boolean;
  hasPreviewed: boolean;
  summary: BuilderState['summary'];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  setPage: (page: number) => void;
  sortField: string | null;
  sortDirection: 'asc' | 'desc';
  toggleSort: (field: string) => void;
}

interface Column {
  id: string;
  label: string;
  sortField?: string;
  render: (row: unknown) => string;
}

function sortIcon(active: boolean, direction: 'asc' | 'desc'): JSX.Element {
  if (!active) return <ArrowUpDown size={12} className="report-preview__sort-idle" aria-hidden />;
  return direction === 'asc' ? (
    <ArrowUp size={12} aria-hidden />
  ) : (
    <ArrowDown size={12} aria-hidden />
  );
}

function columnsForType(reportType: BuilderReportType): Column[] {
  if (reportType === 'inventory') {
    return [
      {
        id: 'serial',
        label: 'Serial',
        sortField: 'serial_number',
        render: (r) => (r as InventoryReportRow).serial_number,
      },
      {
        id: 'brand',
        label: 'Brand',
        sortField: 'brand_name',
        render: (r) => (r as InventoryReportRow).brand_name,
      },
      {
        id: 'model',
        label: 'Model',
        sortField: 'model_name',
        render: (r) =>
          `${(r as InventoryReportRow).model_number} — ${(r as InventoryReportRow).model_name}`,
      },
      {
        id: 'location',
        label: 'Location',
        sortField: 'location_name',
        render: (r) => (r as InventoryReportRow).location_name,
      },
      {
        id: 'status',
        label: 'Status',
        sortField: 'status',
        render: (r) =>
          (r as InventoryReportRow).is_archived ? 'Archived' : (r as InventoryReportRow).status,
      },
      {
        id: 'color',
        label: 'Color',
        sortField: 'color',
        render: (r) => (r as InventoryReportRow).color,
      },
      {
        id: 'created',
        label: 'Date added',
        sortField: 'created_at',
        render: (r) => formatDateTime((r as InventoryReportRow).created_at),
      },
    ];
  }
  if (reportType === 'sales') {
    return [
      {
        id: 'invoice',
        label: 'Invoice',
        sortField: 'invoice_number',
        render: (r) => (r as SalesReportRow).invoice_number,
      },
      {
        id: 'customer',
        label: 'Customer',
        sortField: 'customer_name',
        render: (r) => (r as SalesReportRow).customer_name ?? '—',
      },
      {
        id: 'serial',
        label: 'Serial',
        sortField: 'serial_number',
        render: (r) => (r as SalesReportRow).serial_number,
      },
      {
        id: 'brand',
        label: 'Brand',
        sortField: 'brand_name',
        render: (r) => (r as SalesReportRow).brand_name,
      },
      {
        id: 'model',
        label: 'Model',
        sortField: 'model_name',
        render: (r) =>
          `${(r as SalesReportRow).model_number} — ${(r as SalesReportRow).model_name}`,
      },
      {
        id: 'location',
        label: 'Store',
        sortField: 'location_name',
        render: (r) => (r as SalesReportRow).location_name,
      },
      {
        id: 'payment',
        label: 'Payment',
        sortField: 'payment_mode',
        render: (r) => (r as SalesReportRow).payment_mode ?? '—',
      },
      {
        id: 'source',
        label: 'Source',
        sortField: 'sale_source',
        render: (r) => (r as SalesReportRow).sale_source,
      },
      {
        id: 'sold',
        label: 'Sold at',
        sortField: 'sold_at',
        render: (r) => formatDateTime((r as SalesReportRow).sold_at),
      },
    ];
  }
  if (reportType === 'audit') {
    return [
      {
        id: 'when',
        label: 'When',
        sortField: 'created_at',
        render: (r) => formatDateTime((r as AuditReportRow).created_at),
      },
      {
        id: 'action',
        label: 'Action',
        sortField: 'action',
        render: (r) => (r as AuditReportRow).action,
      },
      {
        id: 'source',
        label: 'Source',
        sortField: 'source',
        render: (r) => (r as AuditReportRow).source,
      },
      {
        id: 'actor',
        label: 'User',
        sortField: 'actor_display_name',
        render: (r) => (r as AuditReportRow).actor_display_name ?? '—',
      },
      {
        id: 'serial',
        label: 'Serial',
        sortField: 'serial_number',
        render: (r) => (r as AuditReportRow).serial_number ?? '—',
      },
      {
        id: 'entity',
        label: 'Entity',
        render: (r) => `${(r as AuditReportRow).entity_type} #${(r as AuditReportRow).entity_id}`,
      },
      { id: 'desc', label: 'Description', render: (r) => (r as AuditReportRow).description ?? '—' },
    ];
  }
  return [
    {
      id: 'when',
      label: 'When',
      sortField: 'created_at',
      render: (r) => formatDateTime((r as NotificationReportRow).created_at),
    },
    {
      id: 'type',
      label: 'Type',
      sortField: 'notification_type',
      render: (r) => (r as NotificationReportRow).notification_type,
    },
    {
      id: 'title',
      label: 'Title',
      sortField: 'title',
      render: (r) => (r as NotificationReportRow).title,
    },
    {
      id: 'severity',
      label: 'Severity',
      sortField: 'severity',
      render: (r) => (r as NotificationReportRow).severity,
    },
    { id: 'status', label: 'Status', render: (r) => (r as NotificationReportRow).status },
    { id: 'desc', label: 'Description', render: (r) => (r as NotificationReportRow).description },
  ];
}

export function ReportPreviewTable({
  reportType,
  rows,
  loading,
  hasPreviewed,
  summary,
  page,
  pageSize,
  totalItems,
  totalPages,
  setPage,
  sortField,
  sortDirection,
  toggleSort,
}: ReportPreviewTableProps): JSX.Element {
  const columns = columnsForType(reportType);
  const pageStart = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = Math.min(page * pageSize, totalItems);

  return (
    <section className="report-preview">
      <header className="report-preview__header">
        <div>
          <h2 className="report-preview__title">Preview results</h2>
          {hasPreviewed && (
            <p className="report-preview__meta">
              <span className="report-preview__count">
                {totalItems.toLocaleString()} row{totalItems === 1 ? '' : 's'}
              </span>
              {summary && reportType === 'inventory' && (
                <span>
                  {' '}
                  · Available {summary.by_status.available ?? 0} · Sold{' '}
                  {summary.by_status.sold ?? 0}
                </span>
              )}
            </p>
          )}
        </div>
      </header>

      <div className="report-preview__table-shell">
        <div className="report-preview__table-scroll">
          <table className="table-root report-preview__table">
            <thead className="report-preview__head">
              <tr>
                {columns.map((column) => (
                  <th
                    key={column.id}
                    className={column.sortField ? 'report-preview__th-sortable' : undefined}
                    onClick={column.sortField ? () => toggleSort(column.sortField!) : undefined}
                  >
                    <span className="report-preview__th-content">
                      {column.label}
                      {column.sortField && sortIcon(sortField === column.sortField, sortDirection)}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading &&
                Array.from({ length: 8 }).map((_, index) => (
                  <tr key={`sk-${index}`}>
                    {columns.map((column) => (
                      <td key={column.id}>
                        <div className="skeleton report-preview__skeleton" />
                      </td>
                    ))}
                  </tr>
                ))}

              {!loading && !hasPreviewed && (
                <tr>
                  <td colSpan={columns.length} className="report-preview__empty">
                    <strong>No preview yet.</strong> Configure filters above, then click Preview
                    results.
                  </td>
                </tr>
              )}

              {!loading && hasPreviewed && rows.length === 0 && (
                <tr>
                  <td colSpan={columns.length} className="report-preview__empty">
                    No rows match the current filters.
                  </td>
                </tr>
              )}

              {!loading &&
                rows.map((row, index) => (
                  <tr key={index}>
                    {columns.map((column) => (
                      <td
                        key={column.id}
                        className={column.id === 'serial' ? 'col-mono' : undefined}
                      >
                        {column.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {hasPreviewed && (
          <div className="report-preview__pagination">
            <span>{totalItems > 0 ? `${pageStart}–${pageEnd} of ${totalItems}` : '0 rows'}</span>
            <div className="report-preview__pagination-controls">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span>
                Page {page} / {Math.max(totalPages, 1)}
              </span>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={page >= totalPages || loading}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
