import { useCallback, useEffect, useMemo, useState } from 'react';
import { canWriteSettings } from '../lib/settings';
import { SettingsService, type TallySettingsGroup } from '../services/api/SettingsService';
import { useAuthStore } from '../store';

interface UseTallySettingsResult {
  tally: TallySettingsGroup | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  canWrite: boolean;
  refresh: () => Promise<void>;
  saveTally: (payload: TallySettingsGroup) => Promise<void>;
}

export function useTallySettings(): UseTallySettingsResult {
  const session = useAuthStore((state) => state.session);
  const canWrite = useMemo(
    () => Boolean(session && canWriteSettings(session.permissions)),
    [session],
  );
  const [tally, setTally] = useState<TallySettingsGroup | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const workspace = await SettingsService.getWorkspace();
      setTally(workspace.tally);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load Tally settings.');
      setTally(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const saveTally = useCallback(async (payload: TallySettingsGroup) => {
    if (!canWrite) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await SettingsService.updateTally(payload);
      setTally(updated);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to save Tally settings.');
      throw err;
    } finally {
      setSaving(false);
    }
  }, [canWrite]);

  return { tally, loading, saving, error, canWrite, refresh, saveTally };
}
