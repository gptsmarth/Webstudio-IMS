import type { CatalogueTab } from '../../lib/catalogue';

interface CatalogueTabBarProps {
  activeTab: CatalogueTab;
  onTabChange: (tab: CatalogueTab) => void;
}

const TABS: Array<{ id: CatalogueTab; label: string }> = [
  { id: 'brands', label: 'Brands' },
  { id: 'locations', label: 'Locations' },
];

export function CatalogueTabBar({ activeTab, onTabChange }: CatalogueTabBarProps): JSX.Element {
  return (
    <div className="cat-tabs" role="tablist" aria-label="Catalogue sections">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          type="button"
          role="tab"
          aria-selected={activeTab === tab.id}
          className={`cat-tabs__item ${activeTab === tab.id ? 'cat-tabs__item--active' : ''}`}
          onClick={() => onTabChange(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
