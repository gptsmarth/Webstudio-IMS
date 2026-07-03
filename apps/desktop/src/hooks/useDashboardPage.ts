import { useCallback, useEffect, useRef, useState } from 'react';
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

export function useDashboardPage(): DashboardPageState {
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
      const [
        snapshot,
        distribution,
        activity,
        notificationResult,
        tallyDashboard,
        apiHealth,
        databaseHealth,
      ] = await Promise.all([
        DashboardService.getOperationsSnapshot(),
        DashboardService.getDistribution(),
        DashboardService.getRecentActivity(12),
        NotificationService.listNotifications({ is_resolved: false, page_size: 8 }),
        TallyService.getDashboard(),
        HealthService.getLive().catch(() => null),
        HealthService.getReady().catch(() => null),
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
  }, []);

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
