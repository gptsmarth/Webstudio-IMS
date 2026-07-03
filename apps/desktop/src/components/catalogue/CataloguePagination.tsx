interface CataloguePaginationProps {
  page: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  loading?: boolean;
}

export function CataloguePagination({
  page,
  pageSize,
  totalItems,
  onPageChange,
  loading = false,
}: CataloguePaginationProps): JSX.Element {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const pageStart = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const pageEnd = Math.min(page * pageSize, totalItems);

  return (
    <div className="cat-table-pagination">
      <span className="cat-table-pagination__meta">
        {totalItems > 0 ? `${pageStart}–${pageEnd} of ${totalItems}` : '0 items'}
      </span>
      <div className="cat-table-pagination__controls">
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={page <= 1 || loading}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span className="cat-table-pagination__page">
          Page {page} / {totalPages}
        </span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={page >= totalPages || loading}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
