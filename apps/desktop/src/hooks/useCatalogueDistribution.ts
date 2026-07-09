import { useCallback, useEffect, useState } from 'react';
import { referenceDataFetchPlan } from '../lib/permissionFetchPlan';
import { DashboardService, type DashboardDistribution } from '../services/api/DashboardService';

export function useCatalogueDistribution(permissions: string[] = []): {
  distribution: DashboardDistribution | null;
  loading: boolean;
  refresh: () => Promise<void>;
} {
  const [distribution, setDistribution] = useState<DashboardDistribution | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const plan = referenceDataFetchPlan(permissions);
    setLoading(true);
    try {
      if (!plan.needsDistribution) {
        setDistribution(null);
        return;
      }
      const data = await DashboardService.getDistribution();
      setDistribution(data);
    } catch {
      setDistribution(null);
    } finally {
      setLoading(false);
    }
  }, [permissions]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { distribution, loading, refresh };
}
