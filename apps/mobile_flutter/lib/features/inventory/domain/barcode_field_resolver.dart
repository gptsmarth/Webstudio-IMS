enum BarcodeFieldTarget { serialNumber, modelNumber, partNumber }

extension BarcodeFieldTargetLabels on BarcodeFieldTarget {
  String get label => switch (this) {
        BarcodeFieldTarget.serialNumber => 'Serial number',
        BarcodeFieldTarget.modelNumber => 'Model number',
        BarcodeFieldTarget.partNumber => 'Part number',
      };

  String get scanHint => switch (this) {
        BarcodeFieldTarget.serialNumber => 'Align the S/N barcode inside the frame',
        BarcodeFieldTarget.modelNumber => 'Align the MODEL barcode inside the frame',
        BarcodeFieldTarget.partNumber => 'Align the P/N barcode inside the frame',
      };
}

class BarcodeScanResult {
  const BarcodeScanResult({
    required this.rawValue,
    required this.format,
    required this.targetField,
    this.inventoryId,
  });

  final String rawValue;
  final String format;
  final BarcodeFieldTarget targetField;
  final String? inventoryId;
}

/// Resolves manufacturer barcode values to inventory fields.
class BarcodeFieldResolver {
  static BarcodeScanResult resolve({
    required String rawValue,
    required String format,
    BarcodeFieldTarget? preferredTarget,
  }) {
    final trimmed = rawValue.trim();
    if (trimmed.isEmpty) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: preferredTarget ?? BarcodeFieldTarget.serialNumber,
      );
    }

    if (preferredTarget != null) {
      final forced = _resolveWithPreference(trimmed, format, preferredTarget);
      if (forced != null) return forced;
    }

    if (_isEanOrUpc(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: trimmed.length <= 8 ? BarcodeFieldTarget.partNumber : BarcodeFieldTarget.modelNumber,
      );
    }

    if (looksLikeManufacturerSerial(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: BarcodeFieldTarget.serialNumber,
      );
    }

    if (looksLikePartNumber(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: BarcodeFieldTarget.partNumber,
      );
    }

    if (looksLikeModelNumber(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: BarcodeFieldTarget.modelNumber,
      );
    }

    return BarcodeScanResult(
      rawValue: trimmed,
      format: format,
      targetField: BarcodeFieldTarget.serialNumber,
    );
  }

  static BarcodeScanResult? _resolveWithPreference(
    String trimmed,
    String format,
    BarcodeFieldTarget preferredTarget,
  ) {
    return switch (preferredTarget) {
      BarcodeFieldTarget.serialNumber when looksLikeManufacturerSerial(trimmed) =>
        BarcodeScanResult(rawValue: trimmed, format: format, targetField: preferredTarget),
      BarcodeFieldTarget.partNumber when looksLikePartNumber(trimmed) =>
        BarcodeScanResult(rawValue: trimmed, format: format, targetField: preferredTarget),
      BarcodeFieldTarget.modelNumber when looksLikeModelNumber(trimmed) =>
        BarcodeScanResult(rawValue: trimmed, format: format, targetField: preferredTarget),
      _ => null,
    };
  }

  static bool _isEanOrUpc(String value) => RegExp(r'^\d{8}$|^\d{12}$|^\d{13}$').hasMatch(value);

  /// Laptop serials such as ASUS `G3N0CX14P199139` (mixed letters + digits, 10+ chars).
  static bool looksLikeManufacturerSerial(String value) {
    final normalized = value.trim().toUpperCase();
    if (normalized.length < 10 || normalized.length > 24) return false;
    if (_isEanOrUpc(normalized)) return false;
    if (_looksLikeAsusPartNumber(normalized)) return false;
    if (!RegExp(r'[A-Z]').hasMatch(normalized)) return false;
    if (!RegExp(r'\d').hasMatch(normalized)) return false;
    return RegExp(r'^[A-Z0-9]+$').hasMatch(normalized);
  }

  static bool _looksLikeAsusPartNumber(String normalized) {
    if (RegExp(r'^90N[A-Z0-9]+').hasMatch(normalized)) return true;
    if (RegExp(r' - M\d').hasMatch(normalized)) return true;
    return false;
  }

  static bool looksLikeModelNumber(String value) {
    if (RegExp(r'^[A-Za-z]{2,8}[A-Za-z0-9]*[-_][A-Za-z0-9]{2,}$').hasMatch(value)) {
      return value.length <= 32;
    }
    return RegExp(r'^[A-Za-z]{2,5}[-_]?\w{3,}$').hasMatch(value) && value.length <= 32;
  }

  /// Manufacturer part numbers — e.g. ASUS `90NB0AU1-M00190`, `ABC-123456`.
  static bool looksLikePartNumber(String value) {
    final normalized = value.trim().toUpperCase();
    if (_looksLikeAsusPartNumber(value)) return true;
    if (RegExp(r'^[A-Z0-9]{2,5}-[A-Z0-9]{4,12}$').hasMatch(normalized)) return true;
    if (RegExp(r'^[A-Z]{2,5}-[0-9]{4,}$').hasMatch(normalized)) return true;
    return false;
  }
}

const supportedBarcodeFormats = [
  'code128',
  'code39',
  'codabar',
  'ean13',
  'ean8',
  'upc_a',
  'upc_e',
  'itf',
  'data_matrix',
];
