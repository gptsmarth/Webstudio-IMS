import { useCallback, useEffect, useState } from 'react';
import { useAuthStore } from '../store';
import { canReadNotifications } from '../services/PermissionService';
import { NotificationService, type NotificationDetail } from '../services/api/NotificationService';

const POLL_MS = 60_000;

export function useNotificationStore() {
  const session = useAuthStore((state) => state.session);
  const canRead = session ? canReadNotifications(session.permissions) : false;
  const [items, setItems] = useState<NotificationDetail[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!canRead) {
      setItems([]);
      setUnreadCount(0);
      return;
    }
    setLoading(true);
    try {
      const result = await NotificationService.listNotifications({ page_size: 100 });
      setItems(result.items);
      setUnreadCount(result.items.filter((item) => !item.is_read).length);
    } catch {
      setItems([]);
      setUnreadCount(0);
    } finally {
      setLoading(false);
    }
  }, [canRead]);

  useEffect(() => {
    if (!canRead) {
      setItems([]);
      setUnreadCount(0);
      return;
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [canRead, refresh]);

  const markRead = useCallback(async (id: number) => {
    await NotificationService.markRead(id);
    setItems((current) => current.map((item) => (
      item.id === id ? { ...item, is_read: true } : item
    )));
    setUnreadCount((count) => Math.max(0, count - 1));
  }, []);

  const archive = useCallback(async (id: number) => {
    await NotificationService.resolve(id);
    await refresh();
  }, [refresh]);

  return { items, unreadCount, loading, refresh, markRead, archive };
}

export const useNotificationCenter = useNotificationStore;
