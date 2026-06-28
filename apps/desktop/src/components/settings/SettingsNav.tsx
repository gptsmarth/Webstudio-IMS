import type { SettingsCategory } from '../../lib/settings';
import { SETTINGS_CATEGORIES } from '../../lib/settings';

interface SettingsNavProps {
  active: SettingsCategory;
  onSelect: (category: SettingsCategory) => void;
}

export function SettingsNav({ active, onSelect }: SettingsNavProps): JSX.Element {
  return (
    <nav className="stg-nav" aria-label="Settings categories">
      {SETTINGS_CATEGORIES.map((item) => (
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
