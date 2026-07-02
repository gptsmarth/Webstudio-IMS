import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CatalogueTab } from '../../lib/catalogue';
import { useCatalogueDistribution } from '../../hooks/useCatalogueDistribution';
import { ProductModelService } from '../../services/api/ProductModelService';
import { useAuthStore } from '../../store';
import {
  BrandsTab,
  CatalogueTabBar,
  LocationsTab,
} from '../../components/catalogue';
import { WorkspacePageBack } from '../../components/shell/WorkspacePageBack';
import { countModelsByBrand } from '../../components/catalogue/BrandsTab';

export function CataloguePage(): JSX.Element {
  const session = useAuthStore((state) => state.session);
  const [activeTab, setActiveTab] = useState<CatalogueTab>('brands');
  const { distribution, refresh: refreshDistribution } = useCatalogueDistribution();
  const [models, setModels] = useState<Awaited<ReturnType<typeof ProductModelService.listModels>>>([]);

  const loadReferenceData = useCallback(async () => {
    try {
      setModels(await ProductModelService.listModels());
    } catch {
      setModels([]);
    }
  }, []);

  useEffect(() => {
    void loadReferenceData();
  }, [loadReferenceData]);

  const onDataChange = () => {
    void refreshDistribution();
    void loadReferenceData();
  };

  const modelCounts = useMemo(() => countModelsByBrand(models), [models]);

  if (!session) {
    return (
      <div className="cat-page">
        <div className="cat-empty"><p>Session unavailable</p></div>
      </div>
    );
  }

  return (
    <div className="cat-page animate-fade-in">
      <header className="cat-page__header">
        <WorkspacePageBack />
        <div>
          <h1 className="cat-page__title">Catalogue</h1>
          <p className="cat-page__subtitle">
            Manage brands and store locations. Product models are created and maintained from Inventory.
            Delete removes catalogue entries permanently when safe — sales, reports, audit history, and backups are preserved.
          </p>
        </div>
      </header>

      <CatalogueTabBar activeTab={activeTab} onTabChange={setActiveTab} />

      <div className="cat-page__panel">
        {activeTab === 'brands' && (
          <BrandsTab
            permissions={session.permissions}
            distributionByBrand={distribution?.by_brand ?? []}
            modelCounts={modelCounts}
            onDataChange={onDataChange}
          />
        )}
        {activeTab === 'locations' && (
          <LocationsTab
            permissions={session.permissions}
            distributionByLocation={distribution?.by_location ?? []}
            onDataChange={onDataChange}
          />
        )}
      </div>
    </div>
  );
}
