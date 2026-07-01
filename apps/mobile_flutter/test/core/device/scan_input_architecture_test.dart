import 'package:flutter_test/flutter_test.dart';

import 'package:webstudio_ims/core/device/scan_input_architecture.dart';
import 'package:webstudio_ims/features/inventory/domain/barcode_field_resolver.dart';

void main() {
  group('ScanInputRegistry', () {
    test('lists implemented and planned sources', () {
      final registry = ScanInputRegistry([
        CameraBarcodeScanSource(() async => const BarcodeScanResult(
              rawValue: 'SN1',
              format: 'code128',
              targetField: BarcodeFieldTarget.serialNumber,
            )),
        const QrScanInputSource(),
        const NfcScanInputSource(),
        const BluetoothScannerInputSource(),
      ]);

      expect(registry.implemented, hasLength(1));
      expect(registry.planned, hasLength(3));
      expect(registry.implemented.first.id, 'camera_barcode');
      expect(registry.planned.map((s) => s.id), ['qr', 'nfc', 'bluetooth_scanner']);
    });

    test('future sources remain unimplemented', () {
      expect(const QrScanInputSource().isImplemented, isFalse);
      expect(const NfcScanInputSource().isImplemented, isFalse);
      expect(const BluetoothScannerInputSource().isImplemented, isFalse);
    });
  });
}
