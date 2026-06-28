import { useCallback, useEffect, useState } from 'react';
import { DashboardService, type DashboardDistribution } from '../services/api/DashboardService';

export function useCatalogueDistribution(): {
  distribution: DashboardDistribution | null;
  loading: boolean;
  refresh: () => Promise<void>;
} {
  const [distribution, setDistribution] = useState<DashboardDistribution | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await DashboardService.getDistribution();
      setDistribution(data);
    } catch {
      setDistribution(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { distribution, loading, refresh };
}
