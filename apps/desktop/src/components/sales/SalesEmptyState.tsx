import { PackageSearch } from 'lucide-react';

interface SalesEmptyStateProps {
  hasFilters: boolean;
  onClearFilters?: () => void;
}

export function SalesEmptyState({ hasFilters, onClearFilters }: SalesEmptyStateProps): JSX.Element {
  return (
    <div className="sales-empty-state">
      <div className="sales-empty-state__icon" aria-hidden>
        <PackageSearch size={28} />
      </div>
      <h3 className="sales-empty-state__title">
        {hasFilters ? 'No sales match your filters' : 'No completed sales yet'}
      </h3>
      <p className="sales-empty-state__text">
        {hasFilters
          ? 'Try clearing filters or broadening your search to see more records.'
          : 'Sales appear here after laptops are marked sold from Inventory.'}
      </p>
      {hasFilters && onClearFilters && (
        <div className="sales-empty-state__actions">
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClearFilters}>
            Reset filters
          </button>
        </div>
      )}
    </div>
  );
}
