import { ApiClientProvider } from './ApiClientProvider';

export interface DeploymentCheck {
  key: string;
  name: string;
  status: string;
  message: string;
  detail: string;
}

export interface IpStrategyRecommendation {
  recommended: string;
  label: string;
  rationale: string;
  alternative: string;
  alternative_rationale: string;
}

export interface OfficeDeploymentDetection {
  generated_at: string;
  overall_status: string;
  checks: DeploymentCheck[];
  recommendations: string[];
  ip_strategy: IpStrategyRecommendation | null;
  server_lan_ip: string;
  hostname: string;
  data_root: string;
  api_port: number;
}

export interface OfficeDeploymentApplyResult {
  saved_settings: Record<string, string>;
  created_directories: string[];
  messages: string[];
}

export interface OfficeDeploymentSummary {
  generated_at: string;
  company_name: string;
  overall_status: string;
  server_lan_ip: string;
  hostname: string;
  data_root: string;
  api_port: number;
  ip_strategy: IpStrategyRecommendation | null;
  checks: DeploymentCheck[];
  recommendations: string[];
  saved_configuration: Record<string, string>;
  created_directories: string[];
  apply_messages: string[];
  client_connection_url: string | null;
  configuration_files_required: boolean;
  administrator_note: string;
}

export interface OfficeDeploymentStatus {
  completed: boolean;
  completed_at: string | null;
  summary_available: boolean;
  summary: OfficeDeploymentSummary | null;
}

export interface OfficeDeploymentCompleteResult {
  detection: OfficeDeploymentDetection;
  apply: OfficeDeploymentApplyResult;
  summary: OfficeDeploymentSummary;
  completed: boolean;
  completed_at: string;
}

export const DeploymentService = {
  async getStatus(): Promise<OfficeDeploymentStatus> {
    const client = await ApiClientProvider.getClient();
    return client.get<OfficeDeploymentStatus>('/api/v1/deployment/office/status');
  },

  async detect(): Promise<OfficeDeploymentDetection> {
    const client = await ApiClientProvider.getClient();
    return client.post<OfficeDeploymentDetection>('/api/v1/deployment/office/detect');
  },

  async apply(): Promise<OfficeDeploymentApplyResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<OfficeDeploymentApplyResult>('/api/v1/deployment/office/apply');
  },

  async complete(): Promise<OfficeDeploymentCompleteResult> {
    const client = await ApiClientProvider.getClient();
    return client.post<OfficeDeploymentCompleteResult>('/api/v1/deployment/office/complete');
  },

  async getSummary(): Promise<{ summary: OfficeDeploymentSummary | null }> {
    const client = await ApiClientProvider.getClient();
    return client.get<{ summary: OfficeDeploymentSummary | null }>('/api/v1/deployment/office/summary');
  },
};
