import type { SettingsCategory } from '../../lib/settings';
import { visibleSettingsCategories } from '../../lib/settings';

interface SettingsNavProps {
  active: SettingsCategory;
  onSelect: (category: SettingsCategory) => void;
  permissions: string[];
}

export function SettingsNav({ active, onSelect, permissions }: SettingsNavProps): JSX.Element {
  const categories = visibleSettingsCategories(permissions);
  return (
    <nav className="stg-nav" aria-label="Settings categories">
      {categories.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`stg-nav__item ${active === item.id ? 'stg-nav__item--active' : ''}`}
          onClick={() => onSelect(item.id)}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
