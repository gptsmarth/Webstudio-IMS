enum BarcodeFieldTarget { serialNumber, modelNumber, partNumber }

extension BarcodeFieldTargetLabels on BarcodeFieldTarget {
  String get label => switch (this) {
        BarcodeFieldTarget.serialNumber => 'Serial number',
        BarcodeFieldTarget.modelNumber => 'Model number',
        BarcodeFieldTarget.partNumber => 'Part number',
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
  }) {
    final trimmed = rawValue.trim();
    if (trimmed.isEmpty) {
      return BarcodeScanResult(rawValue: trimmed, format: format, targetField: BarcodeFieldTarget.serialNumber);
    }

    if (_isEanOrUpc(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: trimmed.length <= 8 ? BarcodeFieldTarget.partNumber : BarcodeFieldTarget.modelNumber,
      );
    }

    if (_looksLikePartNumber(trimmed)) {
      return BarcodeScanResult(
        rawValue: trimmed,
        format: format,
        targetField: BarcodeFieldTarget.partNumber,
      );
    }

    if (_looksLikeModelNumber(trimmed)) {
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

  static bool _isEanOrUpc(String value) => RegExp(r'^\d{8}$|^\d{12}$|^\d{13}$').hasMatch(value);

  static bool _looksLikeModelNumber(String value) {
    return RegExp(r'^[A-Za-z]{2,5}[-_]?\w{3,}$').hasMatch(value) && value.length <= 32;
  }

  static bool _looksLikePartNumber(String value) {
    return RegExp(r'^[A-Z0-9\-]{6,20}$').hasMatch(value) && !value.contains(' ');
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
