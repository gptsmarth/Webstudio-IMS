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

    test('maps ASUS laptop serial numbers', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: 'G3N0CX14P199139',
        format: 'code128',
      );
      expect(result.targetField, BarcodeFieldTarget.serialNumber);
    });

    test('maps ASUS part numbers separately from serials', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '90NB0AU1-M00190',
        format: 'code128',
      );
      expect(result.targetField, BarcodeFieldTarget.partNumber);
    });

    test('maps ASUS model numbers', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: 'UX501VW-FJ019T',
        format: 'code128',
      );
      expect(result.targetField, BarcodeFieldTarget.modelNumber);
    });

    test('maps EAN-8 to part number field', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '96385074',
        format: 'ean8',
      );
      expect(result.targetField, BarcodeFieldTarget.partNumber);
    });

    test('honours explicit preferred target when trust flag is set', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: 'G3N0CX14P199139',
        format: 'code128',
        preferredTarget: BarcodeFieldTarget.modelNumber,
        trustPreferredTarget: true,
      );
      expect(result.targetField, BarcodeFieldTarget.modelNumber);
      expect(result.rawValue, 'G3N0CX14P199139');
    });

    test('exposes human-readable field labels', () {
      expect(BarcodeFieldTarget.modelNumber.label, 'Model number');
    });
  });
}
