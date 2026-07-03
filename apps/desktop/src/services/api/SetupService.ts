import { ApiClientProvider } from './ApiClientProvider';
import { LoggingService } from '../LoggingService';

export interface SetupStatusResponse {
  system_initialized: boolean;
  company_name?: string | null;
  awaiting_recovery_key_confirmation?: boolean;
}

export interface SetupInitializeRequest {
  company_name: string;
  main_admin_name: string;
  username: string;
  password: string;
  confirm_password: string;
}

export interface SetupAdminSummary {
  id: number;
  username: string;
  display_name?: string | null;
  role: string;
  status: string;
  must_change_password?: boolean;
}

export interface SetupInitializeResponse {
  system_initialized?: boolean;
  company_name: string;
  main_admin: SetupAdminSummary;
  recovery_key: string;
}

export interface SetupConfirmRecoveryKeyResponse {
  system_initialized: boolean;
}

export interface MainAdminRecoverPasswordRequest {
  recovery_key: string;
  new_password: string;
  confirm_password: string;
}

export interface MainAdminRecoverPasswordResponse {
  recovery_key: string;
}

export class SetupService {
  static async getStatus(): Promise<SetupStatusResponse> {
    LoggingService.debug('API', 'Fetching setup initialization status');
    const client = await ApiClientProvider.getClient();
    return client.get<SetupStatusResponse>('/api/v1/setup/status');
  }

  static async initialize(data: SetupInitializeRequest): Promise<SetupInitializeResponse> {
    LoggingService.info('API', 'Initializing system setup');
    const client = await ApiClientProvider.getClient();
    return client.post<SetupInitializeResponse>('/api/v1/setup/initialize', data);
  }

  static async confirmRecoveryKey(): Promise<SetupConfirmRecoveryKeyResponse> {
    LoggingService.info('API', 'Confirming master recovery key storage');
    const client = await ApiClientProvider.getClient();
    return client.post<SetupConfirmRecoveryKeyResponse>('/api/v1/setup/confirm-recovery-key');
  }

  static async recoverAdminPassword(
    data: MainAdminRecoverPasswordRequest,
  ): Promise<MainAdminRecoverPasswordResponse> {
    LoggingService.info('API', 'Attempting Main Admin password recovery via recovery key');
    const client = await ApiClientProvider.getClient();
    return client.post<MainAdminRecoverPasswordResponse>(
      '/api/v1/auth/main-admin/recover-password',
      data,
    );
  }
}
