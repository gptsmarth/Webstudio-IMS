import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/features/inventory/domain/barcode_field_resolver.dart';

void main() {
  group('BarcodeFieldResolver', () {
    test('maps EAN-13 to model number field', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '5901234123457',
        format: 'ean13',
      );
      expect(result.targetField, BarcodeFieldTarget.modelNumber);
    });

    test('maps digit-prefixed mixed values to serial by default', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '1234567890abcdef',
        format: 'code128',
      );
      expect(result.targetField, BarcodeFieldTarget.serialNumber);
    });

    test('maps manufacturer Code39 part numbers', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: 'ABC-123456',
        format: 'code39',
      );
      expect(result.targetField, BarcodeFieldTarget.partNumber);
    });

    test('maps EAN-8 to part number field', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '96385074',
        format: 'ean8',
      );
      expect(result.targetField, BarcodeFieldTarget.partNumber);
    });

    test('exposes human-readable field labels', () {
      expect(BarcodeFieldTarget.modelNumber.label, 'Model number');
    });
  });
}
