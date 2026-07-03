import { ConfigService } from './ConfigService';
import { LoggingService } from './LoggingService';
import { UpdateService } from './UpdateService';
import { VersionService } from './VersionService';

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000;
const STORAGE_KEY = 'webstudio_update_remind_later_until';

let intervalId: ReturnType<typeof setInterval> | null = null;

function shouldSuppressOptional(): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    const until = Date.parse(raw);
    return Number.isFinite(until) && Date.now() < until;
  } catch {
    return false;
  }
}

export function remindUpdateLater(hours = 24): void {
  localStorage.setItem(STORAGE_KEY, String(Date.now() + hours * 60 * 60 * 1000));
}

export async function runClientUpdateCheck(options?: { force?: boolean }): Promise<void> {
  try {
    const versionInfo = await VersionService.getVersionInfo();
    const status = await UpdateService.checkForUpdates(versionInfo.appVersion);
    if (!status.updateAvailable || status.error) {
      return;
    }
    if (status.mandatory) {
      await UpdateService.promptAndApplyUpdate(status);
      return;
    }
    if (!options?.force && shouldSuppressOptional()) {
      return;
    }
    await UpdateService.promptAndApplyUpdate(status);
  } catch (error) {
    LoggingService.warn('Main', 'Client update check failed', { error: String(error) });
  }
}

export function startClientUpdatePolling(): void {
  if (intervalId !== null) return;
  void runClientUpdateCheck();
  intervalId = setInterval(() => void runClientUpdateCheck(), CHECK_INTERVAL_MS);
}

export function stopClientUpdatePolling(): void {
  if (intervalId !== null) {
    clearInterval(intervalId);
    intervalId = null;
  }
}

export async function isOnlineForUpdates(): Promise<boolean> {
  try {
    const env = await ConfigService.getEnvironment();
    return Boolean(env.apiBaseUrl);
  } catch {
    return false;
  }
}
