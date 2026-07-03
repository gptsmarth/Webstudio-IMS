import { ConfigService } from './ConfigService';
import { LoggingService } from './LoggingService';
import { ClientUpdateService, type ClientUpdateCheckResult } from './api/ClientUpdateService';
import { remindUpdateLater } from './UpdateCheckLifecycle';

export interface UpdateStatus {
  isChecking: boolean;
  updateAvailable: boolean;
  mandatory?: boolean;
  version?: string;
  releaseNotes?: string | null;
  artifact?: ClientUpdateCheckResult['artifact'];
  error?: string;
}

export class UpdateService {
  static async checkForUpdates(installedVersion: string): Promise<UpdateStatus> {
    LoggingService.info('Main', 'Checking for client updates via WEBSTUDIO Server');
    try {
      const result = await ClientUpdateService.checkForUpdates(installedVersion);
      return {
        isChecking: false,
        updateAvailable: result.update_available,
        mandatory: result.mandatory,
        version: result.latest_version,
        releaseNotes: result.release_notes,
        artifact: result.artifact,
      };
    } catch (error) {
      return {
        isChecking: false,
        updateAvailable: false,
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }

  static async promptAndApplyUpdate(status: UpdateStatus): Promise<void> {
    if (!status.updateAvailable || !status.artifact) {
      return;
    }

    const confirmed = await this.showUpdateDialog(status);
    if (!confirmed) {
      if (!status.mandatory) {
        remindUpdateLater();
      }
      return;
    }

    await this.downloadVerifyInstall(status);
  }

  private static async showUpdateDialog(status: UpdateStatus): Promise<boolean> {
    const title = status.mandatory ? 'Update required' : 'Update available';
    const message = [
      `A new WEBSTUDIO IMS desktop release is available (${status.version}).`,
      status.releaseNotes ? `\n\n${status.releaseNotes}` : '',
      status.mandatory ? '\n\nThis update is required to continue.' : '',
    ].join('');

    if (status.mandatory) {
      return window.confirm(`${title}\n\n${message}\n\nInstall now?`);
    }
    return window.confirm(`${title}\n\n${message}\n\nDownload and install now?`);
  }

  static async downloadUpdate(status: UpdateStatus): Promise<string> {
    if (!status.artifact) {
      throw new Error('No update artifact available');
    }
    const env = await ConfigService.getEnvironment();
    const url = ClientUpdateService.resolveAbsoluteDownloadUrl(status.artifact.download_url, env.apiBaseUrl);
    if (!window.update?.downloadArtifact) {
      throw new Error('Desktop update runtime is unavailable');
    }
    return window.update.downloadArtifact({
      url,
      fileName: status.artifact.name,
      expectedSha256: status.artifact.sha256 ?? undefined,
    });
  }

  static async installUpdate(installerPath: string): Promise<void> {
    if (!window.update?.installAndRestart) {
      throw new Error('Desktop update runtime is unavailable');
    }
    await window.update.installAndRestart(installerPath);
  }

  static async downloadVerifyInstall(status: UpdateStatus): Promise<void> {
    LoggingService.info('Main', 'Downloading client update from server');
    const installerPath = await this.downloadUpdate(status);
    LoggingService.info('Main', 'Installing client update', { installerPath });
    await this.installUpdate(installerPath);
  }
}
