import { useCallback, useEffect, useRef } from 'react';
import { AuthenticationService } from '../services/api/AuthenticationService';
import { AuthTokenStore } from '../services/AuthTokenStore';
import { sessionFromUser, useAuthStore } from '../store/useAuthStore';

const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'touchstart', 'scroll'] as const;

interface UseSessionManagerOptions {
  sessionTimeoutMinutes: number;
  onIdleLogout: () => void;
  enabled?: boolean;
}

export function useSessionManager({
  sessionTimeoutMinutes,
  onIdleLogout,
  enabled = true,
}: UseSessionManagerOptions): void {
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);
  const lastActivityRef = useRef(Date.now());
  const refreshingRef = useRef(false);

  const touchActivity = useCallback(() => {
    lastActivityRef.current = Date.now();
  }, []);

  const refreshIfNeeded = useCallback(async () => {
    if (refreshingRef.current) return;
    const expiresAt = await AuthTokenStore.getAccessExpiresAt();
    if (!expiresAt) return;
    const msUntilExpiry = expiresAt - Date.now();
    if (msUntilExpiry > 60_000) return;
    refreshingRef.current = true;
    try {
      const tokens = await AuthenticationService.refresh();
      const profile = await AuthenticationService.getCurrentUser();
      setSession(
        sessionFromUser({ ...profile, ...tokens.user, permissions: profile.permissions ?? [] }),
      );
    } catch {
      clearSession();
      await AuthTokenStore.clear();
      onIdleLogout();
    } finally {
      refreshingRef.current = false;
    }
  }, [clearSession, onIdleLogout, setSession]);

  useEffect(() => {
    if (!enabled) return;
    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, touchActivity, { passive: true });
    }
    const idleMs = Math.max(sessionTimeoutMinutes, 5) * 60_000;
    const idleTimer = window.setInterval(() => {
      if (Date.now() - lastActivityRef.current >= idleMs) {
        void AuthenticationService.logout().finally(onIdleLogout);
      }
    }, 30_000);
    const refreshTimer = window.setInterval(() => {
      void refreshIfNeeded();
    }, 30_000);
    return () => {
      for (const event of ACTIVITY_EVENTS) {
        window.removeEventListener(event, touchActivity);
      }
      window.clearInterval(idleTimer);
      window.clearInterval(refreshTimer);
    };
  }, [enabled, onIdleLogout, refreshIfNeeded, sessionTimeoutMinutes, touchActivity]);
}
