import { Search } from 'lucide-react';

interface SearchBarProps {
  onOpen: () => void;
}

export function SearchBar({ onOpen }: SearchBarProps): JSX.Element {
  return (
    <button
      type="button"
      className="app-search-trigger"
      onClick={onOpen}
      aria-label="Open global search"
      aria-keyshortcuts="Control+K Meta+K"
    >
      <Search size={14} aria-hidden style={{ color: 'var(--color-text-tertiary)' }} />
      <span className="app-search-placeholder">Search serial, brand, model, location…</span>
      <kbd className="app-kbd" aria-hidden>
        ⌘K
      </kbd>
    </button>
  );
}
