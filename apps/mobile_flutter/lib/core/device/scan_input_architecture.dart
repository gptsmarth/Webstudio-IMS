import '../../features/inventory/domain/barcode_field_resolver.dart';

/// Architecture for alternate scan inputs. Camera barcode is implemented;
/// QR/NFC/Bluetooth scanner adapters are reserved for future hardware.
abstract class ScanInputSource {
  const ScanInputSource();

  String get id;
  String get label;
  bool get isImplemented;

  Future<BarcodeScanResult?> scan();
}

class CameraBarcodeScanSource extends ScanInputSource {
  const CameraBarcodeScanSource(this._openScanner);

  final Future<BarcodeScanResult?> Function() _openScanner;

  @override
  String get id => 'camera_barcode';

  @override
  String get label => 'Camera barcode';

  @override
  bool get isImplemented => true;

  @override
  Future<BarcodeScanResult?> scan() => _openScanner();
}

/// Future-ready QR workflow beyond inventory JSON payloads.
class QrScanInputSource extends ScanInputSource {
  const QrScanInputSource();

  @override
  String get id => 'qr';

  @override
  String get label => 'QR codes';

  @override
  bool get isImplemented => false;

  @override
  Future<BarcodeScanResult?> scan() async {
    throw UnimplementedError('Dedicated QR workflows will plug into ScanInputRegistry.');
  }
}

/// Future-ready NFC tag reader for serial capture.
class NfcScanInputSource extends ScanInputSource {
  const NfcScanInputSource();

  @override
  String get id => 'nfc';

  @override
  String get label => 'NFC tags';

  @override
  bool get isImplemented => false;

  @override
  Future<BarcodeScanResult?> scan() async {
    throw UnimplementedError('NFC reader integration is not enabled on this build.');
  }
}

/// Future-ready Bluetooth HID scanner wedge input.
class BluetoothScannerInputSource extends ScanInputSource {
  const BluetoothScannerInputSource();

  @override
  String get id => 'bluetooth_scanner';

  @override
  String get label => 'Bluetooth scanner';

  @override
  bool get isImplemented => false;

  @override
  Future<BarcodeScanResult?> scan() async {
    throw UnimplementedError('Bluetooth scanner bridge is not enabled on this build.');
  }
}

class ScanInputRegistry {
  const ScanInputRegistry(this.sources);

  final List<ScanInputSource> sources;

  List<ScanInputSource> get implemented => sources.where((s) => s.isImplemented).toList();
  List<ScanInputSource> get planned => sources.where((s) => !s.isImplemented).toList();
}
