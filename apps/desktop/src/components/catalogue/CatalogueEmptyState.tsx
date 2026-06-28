import { FolderOpen } from 'lucide-react';

interface CatalogueEmptyStateProps {
  title: string;
  description: string;
  onClearFilters?: () => void;
  onAdd?: () => void;
  canWrite?: boolean;
  addLabel?: string;
}

export function CatalogueEmptyState({
  title,
  description,
  onClearFilters,
  onAdd,
  canWrite,
  addLabel,
}: CatalogueEmptyStateProps): JSX.Element {
  return (
    <div className="cat-empty-state">
      <div className="cat-empty-state__icon" aria-hidden>
        <FolderOpen size={28} />
      </div>
      <h3 className="cat-empty-state__title">{title}</h3>
      <p className="cat-empty-state__text">{description}</p>
      <div className="cat-empty-state__actions">
        {onClearFilters && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClearFilters}>
            Reset filters
          </button>
        )}
        {canWrite && onAdd && addLabel && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAdd}>
            {addLabel}
          </button>
        )}
      </div>
    </div>
  );
}
