import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/device/scan_input_architecture.dart';
import 'package:webstudio_ims/features/inventory/domain/barcode_field_resolver.dart';

void main() {
  group('QA — Barcode', () {
    test('EAN-13 maps to model number', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: '5901234123457',
        format: 'ean13',
      );
      expect(result.targetField, BarcodeFieldTarget.modelNumber);
    });

    test('manufacturer Code39 part number pattern', () {
      final result = BarcodeFieldResolver.resolve(
        rawValue: 'ABC-123456',
        format: 'code39',
      );
      expect(result.targetField, BarcodeFieldTarget.partNumber);
    });

    test('supported formats list covers manufacturer symbologies', () {
      expect(supportedBarcodeFormats, containsAll(['code128', 'code39', 'ean13', 'ean8', 'data_matrix']));
      expect(supportedBarcodeFormats, isNot(contains('qr')));
    });

    test('scan registry exposes camera as only implemented source', () {
      final registry = ScanInputRegistry([
        CameraBarcodeScanSource(() async => null),
        const QrScanInputSource(),
        const NfcScanInputSource(),
        const BluetoothScannerInputSource(),
      ]);
      expect(registry.implemented, hasLength(1));
      expect(registry.planned, hasLength(3));
    });
  });
}
