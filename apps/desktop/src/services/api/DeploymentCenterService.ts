import { ApiClientProvider } from './ApiClientProvider';

export interface DeploymentPackageItem {
  job_id: number;
  tag_name: string;
  release_version: string;
  build_number: number;
  status: string;
  bundle_dir?: string | null;
  manifest_validated: boolean;
  checksums_verified: boolean;
  completed_at?: string | null;
}

export interface DeploymentCenterDashboard {
  current_version: string | null;
  latest_version: string | null;
  downloaded_version: string | null;
  release_channel: string;
  build_number: number | null;
  git_commit: string | null;
  git_short: string | null;
  release_date: string | null;
  compatibility_status: 'compatible' | 'update_available' | 'incompatible' | 'unknown';
  downloaded_packages: DeploymentPackageItem[];
  deployment_status: string;
  updates_root: string;
  sync_enabled: boolean;
  github_repo: string;
  auto_deploy: boolean;
}

export interface DeploymentEventItem {
  id: number;
  event_type: string;
  status: string;
  release_version?: string | null;
  build_number?: number | null;
  release_channel?: string | null;
  job_id?: number | null;
  administrator_approved: boolean;
  performed_by_user_id?: number | null;
  error_message?: string | null;
  detail: Record<string, unknown>;
  created_at: string;
  completed_at?: string | null;
}

export interface DeploymentEventHistory {
  items: DeploymentEventItem[];
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface DeploymentActionRequest {
  job_id?: number;
  administrator_approved?: boolean;
}

export const DeploymentCenterService = {
  async getDashboard(): Promise<DeploymentCenterDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.get<DeploymentCenterDashboard>('/api/v1/deployment/center/dashboard');
  },

  async refresh(): Promise<DeploymentCenterDashboard> {
    const client = await ApiClientProvider.getClient();
    return client.post<DeploymentCenterDashboard>('/api/v1/deployment/center/refresh');
  },

  async getHistory(page = 1, pageSize = 20): Promise<DeploymentEventHistory> {
    const client = await ApiClientProvider.getClient();
    return client.get<DeploymentEventHistory>(
      `/api/v1/deployment/center/history?page=${page}&page_size=${pageSize}`,
    );
  },

  async getLogs(page = 1, pageSize = 50): Promise<DeploymentEventHistory> {
    const client = await ApiClientProvider.getClient();
    return client.get<DeploymentEventHistory>(
      `/api/v1/deployment/center/logs?page=${page}&page_size=${pageSize}`,
    );
  },

  async checkUpdates(): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/check-updates', {});
  },

  async download(jobId?: number): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/download', {
      job_id: jobId ?? null,
    });
  },

  async validate(jobId: number): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/validate', {
      job_id: jobId,
    });
  },

  async deploy(jobId: number, administratorApproved: boolean): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/deploy', {
      job_id: jobId,
      administrator_approved: administratorApproved,
    });
  },

  async rollback(administratorApproved: boolean): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/rollback', {
      administrator_approved: administratorApproved,
    });
  },

  async deletePackage(
    jobId: number,
    administratorApproved: boolean,
  ): Promise<Record<string, unknown>> {
    const client = await ApiClientProvider.getClient();
    return client.post<Record<string, unknown>>('/api/v1/deployment/center/delete-package', {
      job_id: jobId,
      administrator_approved: administratorApproved,
    });
  },

  async getAnalytics(): Promise<DeploymentAnalytics> {
    const client = await ApiClientProvider.getClient();
    return client.get<DeploymentAnalytics>('/api/v1/deployment/center/analytics');
  },
};

export interface DeploymentAnalyticsSummary {
  sync_enabled: boolean;
  last_github_sync_at: string | null;
  last_github_sync_status: string | null;
  pending_downloads: number;
  failed_downloads: number;
  deployment_run_counts: Record<string, number>;
  rollback_total: number;
  failed_rollbacks: number;
  failed_deployments: number;
  retry_queue_size: number;
}

export interface DeploymentAnalytics {
  generated_at: string;
  summary: DeploymentAnalyticsSummary;
  release_downloads: {
    queue_counts: Record<string, number>;
    recent_completed: Record<string, unknown>[];
    recent_failures: Record<string, unknown>[];
  };
  deployment_history: Record<string, unknown>[];
  deployment_runs: Record<string, unknown>[];
  rollback_history: Record<string, unknown>[];
  deployment_durations: Record<string, unknown>[];
  health_check_history: Record<string, unknown>[];
  desktop_version_distribution: VersionDistributionRow[];
  mobile_version_distribution: VersionDistributionRow[];
  deployment_failures: Record<string, unknown>[];
  retry_queue: Record<string, unknown>[];
  github_polling_history: Record<string, unknown>;
  scheduler_recovery: Record<string, unknown>[];
  tally_scheduler_recovery: Record<string, unknown>;
  backup_scheduler_recovery: Record<string, unknown>;
}

export interface VersionDistributionRow {
  platform: string;
  client_version: string;
  observation_count: number;
  release_channel: string | null;
  first_seen_at: string;
  last_seen_at: string;
}
