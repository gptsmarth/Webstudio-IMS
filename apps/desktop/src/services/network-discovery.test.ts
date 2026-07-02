import { describe, expect, it } from 'vitest';

import {
  buildServerUrl,
  normalizeServerHost,
  normalizeServerUrl,
} from '@webstudio/shared-kernel';

describe('network discovery helpers', () => {
  it('normalizes IPv4 hosts', () => {
    expect(normalizeServerHost('192.168.1.10')).toBe('192.168.1.10');
  });

  it('normalizes hostname and mDNS names', () => {
    expect(normalizeServerHost('WEBSTUDIO-SERVER')).toBe('webstudio-server');
    expect(normalizeServerHost('WEBSTUDIO-SERVER.local')).toBe('webstudio-server.local');
  });

  it('builds URLs with default port', () => {
    expect(normalizeServerUrl('192.168.1.10')).toBe('http://192.168.1.10:8000');
    expect(buildServerUrl('WEBSTUDIO-SERVER.local', 8000)).toBe('http://webstudio-server.local:8000');
  });
});
