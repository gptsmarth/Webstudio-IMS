import {
  CONNECTION_STAGE_LABELS,
  extractHostnameFromUrl,
  normalizeServerUrl,
  type ConnectionDiagnosticsResult,
  type ConnectionStageId,
  type ConnectionStageResult,
} from '@webstudio/shared-kernel';

async function runStage(
  stage: ConnectionStageId,
  action: () => Promise<void>,
): Promise<ConnectionStageResult> {
  try {
    await action();
    return {
      stage,
      label: CONNECTION_STAGE_LABELS[stage],
      success: true,
      message: 'OK',
    };
  } catch (error) {
    return {
      stage,
      label: CONNECTION_STAGE_LABELS[stage],
      success: false,
      message: error instanceof Error ? error.message : String(error),
    };
  }
}

export class ConnectionDiagnosticsService {
  static async testConnection(rawUrl: string): Promise<ConnectionDiagnosticsResult> {
    const stages: ConnectionStageResult[] = [];
    let normalized = rawUrl.trim();

    const hostStage = await runStage('host_resolution', async () => {
      normalized = normalizeServerUrl(rawUrl);
      const hostname = extractHostnameFromUrl(normalized);
      if (!hostname) {
        throw new Error('Could not parse server hostname.');
      }
      if (window.network?.resolveHost) {
        const resolution = await window.network.resolveHost(hostname);
        if (!resolution.resolved) {
          throw new Error(resolution.message || 'Host resolution failed.');
        }
      }
    });
    stages.push(hostStage);
    if (!hostStage.success) {
      return this.buildFailure(normalized, stages, hostStage.stage);
    }

    const reachabilityStage = await runStage('reachability', async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 5000);
      try {
        const response = await fetch(`${normalized}/health/live`, { signal: controller.signal });
        if (response.type === 'opaque') {
          return;
        }
        if (!response.ok && response.status >= 500) {
          throw new Error(`Server unreachable (${response.status}).`);
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          throw new Error('Server did not respond in time.');
        }
        throw error;
      } finally {
        window.clearTimeout(timeout);
      }
    });
    stages.push(reachabilityStage);

    const httpStage = await runStage('http_connection', async () => {
      const response = await fetch(`${normalized}/health/live`, { method: 'GET' });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
    });
    stages.push(httpStage);
    if (!httpStage.success) {
      return this.buildFailure(normalized, stages, httpStage.stage);
    }

    let companyName: string | undefined;
    let backendVersion: string | undefined;

    const healthStage = await runStage('backend_health', async () => {
      const response = await fetch(`${normalized}/health/ready`);
      const body = (await response.json()) as {
        data?: { status?: string; checks?: Record<string, string> };
      };
      if (!response.ok && response.status !== 503) {
        throw new Error(`Health check failed (${response.status}).`);
      }
      const database = body.data?.checks?.database;
      if (database === 'failed') {
        throw new Error('Database is not ready.');
      }
    });
    stages.push(healthStage);
    if (!healthStage.success) {
      return this.buildFailure(normalized, stages, healthStage.stage);
    }

    const apiStage = await runStage('api_compatibility', async () => {
      const response = await fetch(`${normalized}/api/v1/version`);
      if (!response.ok) {
        throw new Error(`Version endpoint failed (${response.status}).`);
      }
      const body = (await response.json()) as {
        data?: { backend_version?: string; api_version?: string };
      };
      backendVersion = body.data?.backend_version;
      if (!body.data?.api_version) {
        throw new Error('API version metadata missing.');
      }
    });
    stages.push(apiStage);
    if (!apiStage.success) {
      return this.buildFailure(normalized, stages, apiStage.stage);
    }

    const authStage = await runStage('authentication_endpoint', async () => {
      const response = await fetch(`${normalized}/api/v1/setup/status`);
      if (!response.ok) {
        throw new Error(`Setup status failed (${response.status}).`);
      }
      const body = (await response.json()) as { data?: { company_name?: string } };
      companyName = body.data?.company_name ?? undefined;
    });
    stages.push(authStage);
    if (!authStage.success) {
      return this.buildFailure(normalized, stages, authStage.stage);
    }

    return {
      success: true,
      url: normalized,
      stages,
      companyName,
      backendVersion,
    };
  }

  private static buildFailure(
    url: string,
    stages: ConnectionStageResult[],
    failedStage: ConnectionStageId,
  ): ConnectionDiagnosticsResult {
    const failed = stages.find((stage) => stage.stage === failedStage);
    return {
      success: false,
      url,
      stages,
      failedStage,
      errorMessage: failed?.message ?? 'Connection failed.',
    };
  }
}
