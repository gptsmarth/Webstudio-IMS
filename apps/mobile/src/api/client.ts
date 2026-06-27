import { createApiClient } from '@webstudio/api-client';

const DEFAULT_API_BASE_URL = 'http://10.0.2.2:8000';

export function createMobileApiClient() {
  return createApiClient({
    baseUrl: process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
    clientPlatform: 'android',
    clientVersion: '0.1.0',
  });
}
