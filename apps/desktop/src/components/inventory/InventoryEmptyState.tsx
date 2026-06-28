import { PackageSearch } from 'lucide-react';

interface InventoryEmptyStateProps {
  hasFilters: boolean;
  onClearFilters?: () => void;
  onAdd?: () => void;
  canWrite: boolean;
}

export function InventoryEmptyState({
  hasFilters,
  onClearFilters,
  onAdd,
  canWrite,
}: InventoryEmptyStateProps): JSX.Element {
  return (
    <div className="inv-empty-state">
      <div className="inv-empty-state__icon" aria-hidden>
        <PackageSearch size={28} />
      </div>
      <h3 className="inv-empty-state__title">
        {hasFilters ? 'No laptops match your filters' : 'No inventory items yet'}
      </h3>
      <p className="inv-empty-state__text">
        {hasFilters
          ? 'Try clearing filters or broadening your search to see more stock.'
          : 'Add your first laptop to start tracking serials, locations, and sales.'}
      </p>
      <div className="inv-empty-state__actions">
        {hasFilters && onClearFilters && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClearFilters}>
            Reset filters
          </button>
        )}
        {canWrite && onAdd && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAdd}>
            Add laptop
          </button>
        )}
      </div>
    </div>
  );
}
