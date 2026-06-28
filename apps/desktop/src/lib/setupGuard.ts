import { SetupService, type SetupStatusResponse } from '../services/api/SetupService';
import { readLocalInitializedFlag } from './setupGuardEvents';

export { dispatchSetupRequired, isSetupRequiredApiError, markLocalInitializedFlag, readLocalInitializedFlag, SETUP_REQUIRED_EVENT } from './setupGuardEvents';

export function isSetupRequired(status: SetupStatusResponse): boolean {
  return !status.system_initialized || Boolean(status.awaiting_recovery_key_confirmation);
}

export function detectDatabaseReset(status: SetupStatusResponse): boolean {
  return readLocalInitializedFlag() && isSetupRequired(status);
}

export async function fetchSetupStatus(): Promise<SetupStatusResponse> {
  return SetupService.getStatus();
}
