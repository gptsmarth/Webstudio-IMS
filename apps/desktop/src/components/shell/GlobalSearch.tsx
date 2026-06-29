import { useEffect, useRef, useState } from 'react';
import { Bell, FileText, Hash, History, MapPin, Package, ScrollText, Search, Tag, X } from 'lucide-react';
import { isRouteAllowedForPermissions } from '../../config/navigation';
import { useDebounce } from '../../lib/useDebounce';
import { useAuthStore, useInventoryStore, useNavigationStore, useSearchStore, useStockNavStore } from '../../store';
import {
  groupSearchResults,
  loadRecentSearches,
  runGlobalSearch,
  saveRecentSearch,
  type SearchResult,
} from '../../services/search/GlobalSearchService';

const TYPE_ICONS = {
  serial: Hash,
  brand: Tag,
  product_model: Package,
  location: MapPin,
  invoice: FileText,
  customer: Tag,
  notification: Bell,
  audit: ScrollText,
} as const;

export function GlobalSearch(): JSX.Element | null {
  const { isOpen, query, close, setQuery } = useSearchStore();
  const session = useAuthStore((state) => state.session);
  const setRoute = useNavigationStore((state) => state.setRoute);
  const setInventoryFocus = useInventoryStore((state) => state.setFocus);
  const setStockSearch = useStockNavStore((state) => state.setSearch);
  const setStockSearchField = useStockNavStore((state) => state.setSearchField);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recent, setRecent] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, 250);

  const openResult = (result: SearchResult) => {
    saveRecentSearch(query.trim());
    const permissions = session?.permissions ?? [];
    const canAccessInventory = isRouteAllowedForPermissions('inventory', permissions);
    const canAccessStock = isRouteAllowedForPermissions('stock', permissions);

    if (!canAccessInventory && canAccessStock) {
      setStockSearch(result.title);
      if (result.type === 'serial') setStockSearchField('serial');
      else if (result.type === 'product_model') setStockSearchField('model_number');
      else if (result.type === 'brand') setStockSearchField('all');
      setRoute('stock');
      close();
      return;
    }

    if (result.type === 'notification') {
      setRoute('notifications');
      close();
      return;
    }
    if (result.type === 'audit') {
      setRoute('audit');
      close();
      return;
    }
    if (result.type === 'product_model') {
      setRoute('catalogue');
      close();
      return;
    }
    if (result.inventoryId && result.type === 'invoice') {
      setRoute('sales');
      close();
      return;
    }
    if (result.inventoryId) {
      setRoute('inventory');
      setInventoryFocus({ itemId: result.inventoryId, search: query.trim() || undefined });
      close();
      return;
    }
    if (result.type === 'brand' || result.type === 'location') {
      setRoute('inventory');
      setInventoryFocus({ search: result.title });
      close();
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    setRecent(loadRecentSearches());
    inputRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') close();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, close]);

  useEffect(() => {
    if (!isOpen) {
      setResults([]);
      return;
    }
    if (!debouncedQuery.trim()) {
      setResults([]);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    void runGlobalSearch(debouncedQuery, session?.permissions).then((items) => {
      if (!cancelled) {
        setResults(items);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, isOpen, session?.permissions]);

  if (!isOpen) return null;

  const grouped = groupSearchResults(results);

  return (
    <div className="app-search-overlay" role="presentation" onClick={close}>
      <div
        className="app-search-dialog animate-slide-in"
        role="dialog"
        aria-modal="true"
        aria-label="Global search"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="app-search-input-row">
          <Search size={16} aria-hidden style={{ color: 'var(--color-text-tertiary)' }} />
          <input
            ref={inputRef}
            type="search"
            className="app-search-input"
            placeholder="Search inventory, sales, catalogue, notifications, audit…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-label="Search query"
          />
          <button type="button" className="app-toolbar-icon-btn" onClick={close} aria-label="Close search">
            <X size={16} aria-hidden />
          </button>
        </div>

        <div className="app-search-body">
          {!query.trim() && recent.length > 0 && (
            <div className="app-search-recent">
              <p className="app-search-recent__title"><History size={12} aria-hidden /> Recent searches</p>
              <ul className="app-search-recent__list">
                {recent.map((entry) => (
                  <li key={entry}>
                    <button type="button" className="app-search-recent__item" onClick={() => setQuery(entry)}>
                      {entry}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!query.trim() && recent.length === 0 && (
            <p className="app-search-hint">
              Search serial numbers, brands, product models, locations, invoices, notifications, and audit logs.
            </p>
          )}
          {query.trim() && loading && <p className="app-search-hint">Searching…</p>}
          {query.trim() && !loading && results.length === 0 && (
            <p className="app-search-empty">No results for “{query.trim()}”.</p>
          )}
          {grouped.map((section) => (
            <div key={section.group} className="app-search-group">
              <p className="app-search-group__title">{section.group}</p>
              <ul className="app-search-results" role="listbox" aria-label={`${section.group} results`}>
                {section.items.map((result) => {
                  const Icon = TYPE_ICONS[result.type] ?? Package;
                  return (
                    <li key={result.id} role="option">
                      <button type="button" className="app-search-result" onClick={() => openResult(result)}>
                        <Icon size={14} aria-hidden style={{ color: 'var(--color-primary-500)' }} />
                        <span className="app-search-result-text">
                          <span className="app-search-result-title">{result.title}</span>
                          {result.subtitle && <span className="app-search-result-subtitle">{result.subtitle}</span>}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
