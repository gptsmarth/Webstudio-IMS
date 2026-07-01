import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/reports/domain/report_models.dart';
import 'package:webstudio_ims/features/settings/domain/settings_models.dart';

void main() {
  test('ReportQueryParams maps tally notification filters', () {
    const params = ReportQueryParams(syncStatus: 'unread', tallyOutcome: 'processed');
    final query = params.toQueryParams(ReportType.tally);
    expect(query['notification_category'], 'tally_sync');
    expect(query['status'], 'unread');
    expect(query['notification_type'], 'tally_sync_completed');
  });

  test('ReportQueryParams maps inventory status filters', () {
    const params = ReportQueryParams(inventoryStatus: 'available');
    final query = params.toQueryParams(ReportType.inventory);
    expect(query['status'], 'available');
    expect(query['is_archived'], false);
  });

  test('SettingsWorkspaceSummary parses backup and AI health', () {
    final summary = SettingsWorkspaceSummary.fromJson({
      'general': {'company_name': 'WEBSTUDIO'},
      'system': {'app_version': '1.0.0'},
      'backup': {
        'health_status': 'healthy',
        'backup_folder': '/data/backups',
        'retention_policy': 'count:7',
        'database_size_bytes': 1024,
      },
      'tally': {
        'connection_status': 'connected',
        'enabled': true,
        'tally_host': '127.0.0.1',
        'tally_port': '9000',
      },
      'integrations': {
        'gemini_configured': true,
        'ai_enrichment_enabled': true,
        'gemini_model': 'gemini-2.0-flash',
        'ai_provider_health': [
          {'provider': 'gemini', 'configured': true, 'status': 'healthy'},
        ],
      },
    });
    expect(summary.companyName, 'WEBSTUDIO');
    expect(summary.backup.healthStatus, 'healthy');
    expect(summary.integrations.aiProviderHealth.first.status, 'healthy');
  });

  test('formatBytes renders human readable sizes', () {
    expect(formatBytes(0), '0 B');
    expect(formatBytes(2048), '2.0 KB');
  });
}
