import { Search } from 'lucide-react';
import {
  HIERARCHY_SEARCH_FIELDS,
  hierarchySearchPlaceholder,
  type HierarchySearchField,
} from '../../lib/hierarchySearch';
import type { ProductCategoryFilter } from '../../lib/productCategory';
import { PRODUCT_CATEGORY_FILTERS } from '../../lib/productCategory';

interface HierarchyToolbarProps {
  search: string;
  onSearchChange: (value: string) => void;
  searchField?: HierarchySearchField;
  onSearchFieldChange?: (value: HierarchySearchField) => void;
  productCategoryFilter?: ProductCategoryFilter;
  onProductCategoryFilterChange?: (value: ProductCategoryFilter) => void;
  placeholder?: string;
  showZeroStock?: boolean;
  onToggleZeroStock?: (value: boolean) => void;
}

export function HierarchyToolbar({
  search,
  onSearchChange,
  searchField = 'all',
  onSearchFieldChange,
  productCategoryFilter = 'all',
  onProductCategoryFilterChange,
  placeholder,
  showZeroStock,
  onToggleZeroStock,
}: HierarchyToolbarProps): JSX.Element {
  const resolvedPlaceholder = placeholder ?? hierarchySearchPlaceholder(searchField);

  return (
    <div className="hierarchy-toolbar">
      {onProductCategoryFilterChange && (
        <label className="toolbar-field hierarchy-toolbar__filter">
          <span className="toolbar-field__label">Show</span>
          <select
            className="input hierarchy-toolbar__filter-select"
            value={productCategoryFilter}
            onChange={(event) =>
              onProductCategoryFilterChange(event.target.value as ProductCategoryFilter)
            }
          >
            {PRODUCT_CATEGORY_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      )}
      {onSearchFieldChange && (
        <label className="toolbar-field hierarchy-toolbar__filter">
          <span className="toolbar-field__label">Search by</span>
          <select
            className="input hierarchy-toolbar__filter-select"
            value={searchField}
            onChange={(event) => onSearchFieldChange(event.target.value as HierarchySearchField)}
          >
            {HIERARCHY_SEARCH_FIELDS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="toolbar-field hierarchy-toolbar__search">
        <span className="toolbar-field__label">Search</span>
        <div className="toolbar-search-control">
          <Search size={15} className="toolbar-search-control__icon" aria-hidden />
          <input
            type="search"
            className="input hierarchy-toolbar__search-input"
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder={resolvedPlaceholder}
          />
        </div>
      </label>
      {onToggleZeroStock && (
        <label className="hierarchy-toolbar__checkbox">
          <input
            type="checkbox"
            checked={showZeroStock}
            onChange={(event) => onToggleZeroStock(event.target.checked)}
          />
          <span>Show zero stock</span>
        </label>
      )}
    </div>
  );
}
