import 'package:flutter_test/flutter_test.dart';
import 'package:webstudio_ims/core/network/json_map.dart';
import 'package:webstudio_ims/features/audit/domain/audit_models.dart';

void main() {
  test('AuditLogEntry parses enriched audit list rows', () {
    final entry = AuditLogEntry.fromJson(asJsonMap({
      'id': 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      'module': 'Inventory',
      'operation': 'Create',
      'description': 'Added laptop SN-001',
      'created_at': '2026-06-27T10:00:00Z',
      'actor_display_name': 'ARVIND SINGH',
      'severity': 'low',
    }));

    expect(entry.id, 'f47ac10b-58cc-4372-a567-0e02b2c3d479');
    expect(entry.module, 'Inventory');
    expect(entry.operation, 'Create');
    expect(entry.actorDisplayName, 'ARVIND SINGH');
  });

  test('asJsonMapList coerces audit envelope data list', () {
    final rows = asJsonMapList([
      {'id': '1', 'module': 'Sales', 'operation': 'Update', 'description': 'Sold unit'},
    ]);
    expect(rows, hasLength(1));
    expect(rows.first['module'], 'Sales');
  });
}
