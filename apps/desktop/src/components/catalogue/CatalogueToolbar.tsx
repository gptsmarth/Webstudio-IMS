import { Download, Plus, RefreshCw, Search } from 'lucide-react';

interface CatalogueToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder: string;
  canWrite: boolean;
  canExport: boolean;
  onAdd?: () => void;
  addLabel: string;
  onExport?: () => void;
  onRefresh: () => void;
  loading: boolean;
  includeArchived?: boolean;
  onIncludeArchivedChange?: (value: boolean) => void;
}

export function CatalogueToolbar({
  search,
  onSearchChange,
  searchPlaceholder,
  canWrite,
  canExport,
  onAdd,
  addLabel,
  onExport,
  onRefresh,
  loading,
  includeArchived = false,
  onIncludeArchivedChange,
}: CatalogueToolbarProps): JSX.Element {
  return (
    <div className="cat-toolbar">
      <div className="cat-toolbar__search">
        <Search size={15} aria-hidden className="cat-toolbar__search-icon" />
        <input
          type="search"
          className="input cat-toolbar__search-input"
          placeholder={searchPlaceholder}
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>
      {onIncludeArchivedChange && (
        <label className="cat-toolbar__checkbox">
          <input
            type="checkbox"
            checked={includeArchived}
            onChange={(event) => onIncludeArchivedChange(event.target.checked)}
          />
          <span>Include archived</span>
        </label>
      )}
      <div className="cat-toolbar__actions">
        {canWrite && onAdd && (
          <button type="button" className="btn btn-primary btn-sm" onClick={onAdd}>
            <Plus size={14} aria-hidden />
            {addLabel}
          </button>
        )}
        {canExport && onExport && (
          <button type="button" className="btn btn-secondary btn-sm" onClick={onExport}>
            <Download size={14} aria-hidden />
            Export
          </button>
        )}
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh"
        >
          <RefreshCw size={14} aria-hidden className={loading ? 'cat-spin' : undefined} />
        </button>
      </div>
    </div>
  );
}
