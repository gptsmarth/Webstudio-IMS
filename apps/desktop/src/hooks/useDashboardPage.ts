import { useCallback, useEffect, useRef, useState } from 'react';
import { canViewDashboardWidget, P, PermissionService } from '../services/PermissionService';
import {
  DashboardService,
  type DashboardDistribution,
  type OperationsDashboard,
  type RecentActivityEntry,
} from '../services/api/DashboardService';
import { HealthService, type HealthLive, type HealthReady } from '../services/api/HealthService';
import { NotificationService, type NotificationDetail } from '../services/api/NotificationService';
import { TallyService, type TallyStatusSummary } from '../services/api/TallyService';

const REFRESH_MS = 45_000;

export interface DashboardPageData {
  snapshot: OperationsDashboard | null;
  distribution: DashboardDistribution | null;
  activity: RecentActivityEntry[];
  notifications: NotificationDetail[];
  unreadCount: number;
  tally: TallyStatusSummary;
  apiHealth: HealthLive | null;
  databaseHealth: HealthReady | null;
}

interface DashboardPageState {
  data: DashboardPageData;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  markNotificationRead: (id: number) => Promise<void>;
  resolveNotification: (id: number) => Promise<void>;
  triggerTallySync: () => Promise<void>;
  syncingTally: boolean;
}

const EMPTY_DATA: DashboardPageData = {
  snapshot: null,
  distribution: null,
  activity: [],
  notifications: [],
  unreadCount: 0,
  tally: TallyService.toSummary(null),
  apiHealth: null,
  databaseHealth: null,
};

function dashboardFetchPlan(permissions: string[]) {
  const permissionService = PermissionService.from(permissions);
  const canWidget = (widget: string) => canViewDashboardWidget(permissions, widget);

  const needsDistribution =
    permissionService.has(P.inventory.view) &&
    (canWidget(P.dashboard.inventoryDistribution) ||
      canWidget(P.dashboard.brandDistribution) ||
      canWidget(P.dashboard.storeStatus));

  const needsActivity =
    permissionService.has(P.dashboard.view) &&
    (canWidget(P.dashboard.recentSales) ||
      canWidget(P.dashboard.recentInventory) ||
      canWidget(P.dashboard.recentTransfers) ||
      canWidget(P.dashboard.recentActivity));

  return {
    needsSnapshot: permissionService.has(P.dashboard.view),
    needsDistribution,
    needsActivity,
    needsNotifications:
      permissionService.has(P.notifications.view) && canWidget(P.dashboard.notifications),
    needsTally: permissionService.has(P.tally.viewStatus),
    needsSystemHealth: canWidget(P.dashboard.systemStatus),
  };
}

export function useDashboardPage(permissions: string[] = []): DashboardPageState {
  const [data, setData] = useState<DashboardPageData>(EMPTY_DATA);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncingTally, setSyncingTally] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const plan = dashboardFetchPlan(permissions);
      const [
        snapshot,
        distribution,
        activity,
        notificationResult,
        tallyDashboard,
        apiHealth,
        databaseHealth,
      ] = await Promise.all([
        plan.needsSnapshot ? DashboardService.getOperationsSnapshot() : Promise.resolve(null),
        plan.needsDistribution ? DashboardService.getDistribution() : Promise.resolve(null),
        plan.needsActivity ? DashboardService.getRecentActivity(12) : Promise.resolve([]),
        plan.needsNotifications
          ? NotificationService.listNotifications({ is_resolved: false, page_size: 8 })
          : Promise.resolve({ items: [], total_items: 0 }),
        plan.needsTally ? TallyService.getDashboard() : Promise.resolve(null),
        plan.needsSystemHealth ? HealthService.getLive().catch(() => null) : Promise.resolve(null),
        plan.needsSystemHealth ? HealthService.getReady().catch(() => null) : Promise.resolve(null),
      ]);

      if (!mountedRef.current) return;

      const unreadCount = notificationResult.items.filter((item) => !item.is_read).length;

      setData({
        snapshot,
        distribution,
        activity,
        notifications: notificationResult.items,
        unreadCount: notificationResult.total_items || unreadCount,
        tally: TallyService.toSummary(tallyDashboard),
        apiHealth,
        databaseHealth,
      });
    } catch (err: unknown) {
      if (!mountedRef.current) return;
      const message = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(
        message.response?.data?.detail ?? message.message ?? 'Unable to load dashboard data.',
      );
      setData(EMPTY_DATA);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [permissions]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const markNotificationRead = useCallback(
    async (id: number) => {
      await NotificationService.markRead(id);
      await refresh();
    },
    [refresh],
  );

  const resolveNotification = useCallback(
    async (id: number) => {
      await NotificationService.resolve(id);
      await refresh();
    },
    [refresh],
  );

  const triggerTallySync = useCallback(async () => {
    setSyncingTally(true);
    try {
      await TallyService.triggerSync();
      await refresh();
    } finally {
      setSyncingTally(false);
    }
  }, [refresh]);

  return {
    data,
    loading,
    error,
    refresh,
    markNotificationRead,
    resolveNotification,
    triggerTallySync,
    syncingTally,
  };
}
