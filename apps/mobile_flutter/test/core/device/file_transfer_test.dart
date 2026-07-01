import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/device/file_transfer_service.dart';

void main() {
  group('parseContentDispositionFilename', () {
    test('extracts quoted filename', () {
      expect(
        parseContentDispositionFilename('attachment; filename="sales-report.xlsx"', 'fallback.xlsx'),
        'sales-report.xlsx',
      );
    });

    test('falls back when header missing', () {
      expect(parseContentDispositionFilename(null, 'report.xlsx'), 'report.xlsx');
    });
  });

  group('exportExtensionForFormat', () {
    test('maps pdf and xlsx', () {
      expect(exportExtensionForFormat('pdf'), 'pdf');
      expect(exportExtensionForFormat('xlsx'), 'xlsx');
    });
  });
}
