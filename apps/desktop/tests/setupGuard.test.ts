import { describe, expect, it } from 'vitest';
import { isSetupRequiredApiError } from '../src/lib/setupGuardEvents';

describe('setupGuardEvents', () => {
  it('detects not initialized message in API envelope', () => {
    const err = {
      response: {
        status: 403,
        data: { error: { message: 'System is not initialized', code: 'PERMISSION_DENIED' } },
      },
    };
    expect(isSetupRequiredApiError(err)).toBe(true);
  });

  it('detects SYSTEM_NOT_INITIALIZED code', () => {
    const err = {
      response: {
        status: 403,
        data: { error: { message: 'Forbidden', code: 'SYSTEM_NOT_INITIALIZED' } },
      },
    };
    expect(isSetupRequiredApiError(err)).toBe(true);
  });

  it('ignores generic auth failures', () => {
    const err = {
      response: {
        status: 401,
        data: { error: { message: 'Invalid username or password', code: 'AUTHENTICATION_FAILED' } },
      },
    };
    expect(isSetupRequiredApiError(err)).toBe(false);
  });
});
