import { useCallback, useEffect, useState } from 'react';
import type { SettingsCategory } from '../lib/settings';
import { LocationService, type Location } from '../services/api/LocationService';
import {
  SettingsService,
  type BackupSettingsUpdate,
  type IntegrationsSettingsUpdate,
  type SettingsWorkspace,
} from '../services/api/SettingsService';

export interface SettingsWorkspaceState {
  category: SettingsCategory;
  setCategory: (category: SettingsCategory) => void;
  workspace: SettingsWorkspace | null;
  locations: Location[];
  loading: boolean;
  error: string | null;
  saving: boolean;
  actionError: string | null;
  clearActionError: () => void;
  refresh: () => Promise<void>;
  saveGeneral: (payload: SettingsWorkspace['general']) => Promise<void>;
  saveSecurity: (payload: SettingsWorkspace['security']) => Promise<void>;
  saveInventory: (payload: SettingsWorkspace['inventory']) => Promise<void>;
  saveSales: (payload: SettingsWorkspace['sales']) => Promise<void>;
  saveTally: (payload: SettingsWorkspace['tally']) => Promise<void>;
  saveIntegrations: (payload: IntegrationsSettingsUpdate) => Promise<void>;
  saveExcel: (payload: SettingsWorkspace['excel']) => Promise<void>;
  saveNotifications: (payload: SettingsWorkspace['notifications']) => Promise<void>;
  saveBackup: (payload: BackupSettingsUpdate) => Promise<void>;
  createBackup: () => Promise<void>;
  restoreBackup: (filename: string) => Promise<void>;
  canWrite: boolean;
}

export function useSettingsWorkspace(canWrite: boolean): SettingsWorkspaceState {
  const [category, setCategory] = useState<SettingsCategory>('general');
  const [workspace, setWorkspace] = useState<SettingsWorkspace | null>(null);
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, locationRows] = await Promise.all([
        SettingsService.getWorkspace(),
        LocationService.listLocations().catch(() => []),
      ]);
      setWorkspace(data);
      setLocations(locationRows);
    } catch (err: unknown) {
      const message = err as { message?: string };
      setError(message.message ?? 'Unable to load settings.');
      setWorkspace(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const runSave = useCallback(
    async (
      action: () => Promise<SettingsWorkspace[keyof SettingsWorkspace]>,
      section: keyof SettingsWorkspace,
    ) => {
      if (!canWrite) return;
      setSaving(true);
      setActionError(null);
      try {
        await action();
        await refresh();
      } catch (err: unknown) {
        const message = err as { message?: string };
        setActionError(message.message ?? `Unable to save ${section} settings.`);
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [canWrite, refresh],
  );

  const saveGeneral = useCallback(
    async (payload: SettingsWorkspace['general']) => {
      await runSave(() => SettingsService.updateGeneral(payload), 'general');
    },
    [runSave],
  );

  const saveSecurity = useCallback(
    async (payload: SettingsWorkspace['security']) => {
      await runSave(() => SettingsService.updateSecurity(payload), 'security');
    },
    [runSave],
  );

  const saveInventory = useCallback(
    async (payload: SettingsWorkspace['inventory']) => {
      await runSave(() => SettingsService.updateInventory(payload), 'inventory');
    },
    [runSave],
  );

  const saveSales = useCallback(
    async (payload: SettingsWorkspace['sales']) => {
      await runSave(() => SettingsService.updateSales(payload), 'sales');
    },
    [runSave],
  );

  const saveTally = useCallback(
    async (payload: SettingsWorkspace['tally']) => {
      await runSave(() => SettingsService.updateTally(payload), 'tally');
    },
    [runSave],
  );

  const saveIntegrations = useCallback(
    async (payload: IntegrationsSettingsUpdate) => {
      await runSave(() => SettingsService.updateIntegrations(payload), 'integrations');
    },
    [runSave],
  );

  const saveExcel = useCallback(
    async (payload: SettingsWorkspace['excel']) => {
      await runSave(() => SettingsService.updateExcel(payload), 'excel');
    },
    [runSave],
  );

  const saveNotifications = useCallback(
    async (payload: SettingsWorkspace['notifications']) => {
      await runSave(() => SettingsService.updateNotifications(payload), 'notifications');
    },
    [runSave],
  );

  const saveBackup = useCallback(
    async (payload: BackupSettingsUpdate) => {
      await runSave(() => SettingsService.updateBackup(payload), 'backup');
    },
    [runSave],
  );

  const createBackup = useCallback(async () => {
    if (!canWrite) return;
    setSaving(true);
    setActionError(null);
    try {
      await SettingsService.createBackup();
      await refresh();
    } catch (err: unknown) {
      const message = err as { message?: string };
      setActionError(message.message ?? 'Backup failed.');
      throw err;
    } finally {
      setSaving(false);
    }
  }, [canWrite, refresh]);

  const restoreBackup = useCallback(
    async (filename: string) => {
      if (!canWrite) return;
      setSaving(true);
      setActionError(null);
      try {
        await SettingsService.restoreBackup({ filename, confirmed: true });
        await refresh();
      } catch (err: unknown) {
        const message = err as { message?: string };
        setActionError(message.message ?? 'Restore failed.');
        throw err;
      } finally {
        setSaving(false);
      }
    },
    [canWrite, refresh],
  );

  return {
    category,
    setCategory,
    workspace,
    locations,
    loading,
    error,
    saving,
    actionError,
    clearActionError: () => setActionError(null),
    refresh,
    saveGeneral,
    saveSecurity,
    saveInventory,
    saveSales,
    saveTally,
    saveIntegrations,
    saveExcel,
    saveNotifications,
    saveBackup,
    createBackup,
    restoreBackup,
    canWrite,
  };
}
