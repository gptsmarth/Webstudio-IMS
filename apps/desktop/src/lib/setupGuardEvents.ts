const INITIALIZED_FLAG_KEY = 'webstudio_system_initialized';

export const SETUP_REQUIRED_EVENT = 'webstudio:setup-required';

export function readLocalInitializedFlag(): boolean {
  try {
    return localStorage.getItem(INITIALIZED_FLAG_KEY) === 'true';
  } catch {
    return false;
  }
}

export function markLocalInitializedFlag(value: boolean): void {
  try {
    if (value) {
      localStorage.setItem(INITIALIZED_FLAG_KEY, 'true');
    } else {
      localStorage.removeItem(INITIALIZED_FLAG_KEY);
    }
  } catch {
    // ignore storage errors
  }
}

export function dispatchSetupRequired(reason: string): void {
  markLocalInitializedFlag(false);
  window.dispatchEvent(new CustomEvent(SETUP_REQUIRED_EVENT, { detail: { reason } }));
}

export function isSetupRequiredApiError(err: unknown): boolean {
  const error = err as {
    response?: { status?: number; data?: { error?: { message?: string; code?: string } } };
    message?: string;
  };
  const status = error.response?.status;
  const message = (error.response?.data?.error?.message ?? error.message ?? '').toLowerCase();
  if (message.includes('not initialized')) return true;
  if (status === 403 && error.response?.data?.error?.code === 'SYSTEM_NOT_INITIALIZED') return true;
  return false;
}
